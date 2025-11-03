from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

# Se han eliminado las importaciones de CONF_PLANT_ID y CONF_EMS_TOKEN
from .const import (
    DOMAIN,
    HARDCODED_API_URL,
    CONF_API_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_GREEN_DEVICES,
    CONF_YELLOW_DEVICES,
)

_LOGGER = logging.getLogger(__name__)

# Plataformas que este componente cargará (sensores)
PLATFORMS: list[str] = ["sensor"]


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle entry reload."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Spock Energy Control from a config entry."""
    cfg = {**entry.data, **entry.options}
    coordinator = SpockEnergyCoordinator(hass, cfg)

    # Estructura por entry_id (guardamos también el unsub del ticker)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "unsub": None,
    }

    # Reactivar al cambiar opciones
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Primer fetch y programación del ciclo
    await asyncio.sleep(2)
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.info("Spock Energy Control: primer fetch realizado.")

    interval = coordinator.update_interval or timedelta(seconds=60)

    async def _tick(_now):
        try:
            _LOGGER.debug("Spock Energy Control tick → async_request_refresh()")
            await coordinator.async_request_refresh()
        except Exception as exc:  # noqa: BLE001
            _LOGGER.exception("Tick error: %s", exc)

    unsub = async_track_time_interval(hass, _tick, interval)
    hass.data[DOMAIN][entry.entry_id]["unsub"] = unsub
    _LOGGER.info("Spock Energy Control: ciclo programado cada %s.", interval)

    # Carga las plataformas (sensor.py)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # 1. Descarga las plataformas (sensor.py)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    # 2. Cancela el ticker
    entry_data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if entry_data and entry_data.get("unsub"):
        entry_data["unsub"]()  # cancelar ticker
    
    return unload_ok


class SpockEnergyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator que consulta el endpoint y ejecuta acciones SGReady."""

    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        """Initialize coordinator."""
        self.config = config
        self.api_token: str = config[CONF_API_TOKEN]
        self.green_devices: list[str] = config.get(CONF_GREEN_DEVICES, [])
        self.yellow_devices: list[str] = config.get(CONF_YELLOW_DEVICES, [])
        self._session = async_get_clientsession(hass)
        
        # No hay lógica de CONF_PLANT_ID o CONF_EMS_TOKEN aquí.

        # Intervalo desde opciones (mínimo 10s)
        seconds = 60
        try:
            seconds = max(10, int(config.get(CONF_SCAN_INTERVAL, 60)))
        except Exception:
            pass

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=seconds),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint."""
        _LOGGER.debug("Fetching API data from %s", HARDCODED_API_URL)
        try:
            headers = {"X-Auth-Token": self.api_token}
            async with self._session.get(HARDCODED_API_URL, headers=headers) as resp:
                if resp.status == 403:
                    raise UpdateFailed("API Token inválido (403)")
                if resp.status != 200:
                    txt = await resp.text()
                    _LOGGER.error("API error %s: %s", resp.status, txt)
                    raise UpdateFailed(f"HTTP {resp.status}")

                data = await resp.json(content_type=None)

            # Validación mínima
            if not isinstance(data, dict) or "green" not in data or "yellow" not in data:
                raise UpdateFailed(f"Formato de respuesta inesperado: {data}")

            await self._execute_sgready_actions(data)
            return data

        except UpdateFailed:
            raise
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Fetcher error: {err}") from err

    async def _execute_sgready_actions(self, status: dict) -> None:
        """Execute SGReady actions based on API status."""
        groups = {"green": self.green_devices, "yellow": self.yellow_devices}

        for group, api_state in status.items():
            all_targets = groups.get(group) or []
            if not all_targets:
                _LOGGER.debug("Sin dispositivos en grupo %s; se omite.", group)
                continue

            # 1. Determinar el servicio y el estado deseado
            service_to_call: str | None = None
            desired_state: str | None = None

            if api_state == "start":
                service_to_call = "turn_on"
                desired_state = "on"
            elif api_state == "stop":
                service_to_call = "turn_off"
                desired_state = "off"

            if not service_to_call or not desired_state:
                _LOGGER.warning("Estado desconocido para %s: %s", group, api_state)
                continue

            # 2. Filtrar entidades que realmente necesitan la acción
            entities_to_action = []
            for entity_id in all_targets:
                try:
                    current_state_obj = self.hass.states.get(entity_id)

                    if not current_state_obj:
                        _LOGGER.warning(
                            "No se pudo encontrar el estado de la entidad '%s' (grupo %s). Se omitirá.",
                            entity_id,
                            group,
                        )
                        continue

                    current_state = current_state_obj.state
                    _LOGGER.debug(
                        "Entidad %s: API quiere '%s' (estado %s), estado actual es '%s'",
                        entity_id,
                        api_state,
                        desired_state,
                        current_state,
                    )

                    # 3. Comparar estado actual con deseado
                    if current_state != desired_state:
                        entities_to_action.append(entity_id)
                    else:
                        _LOGGER.debug(
                            "Entidad %s ya está en el estado deseado (%s). No se envía acción.",
                            entity_id,
                            desired_state,
                        )

                except Exception as e:
                    _LOGGER.error("Error al procesar entidad %s: %s", entity_id, e)

            # 4. Ejecutar la llamada al servicio SOLO si hay entidades que cambiar
            if entities_to_action:
                _LOGGER.info(
                    "Acción %s (desde API=%s) para %s: %s",
                    service_to_call,
                    api_state,
                    group,
                    entities_to_action,
                )
                await self.hass.services.async_call(
                    "homeassistant",
                    service_to_call,
                    {"entity_id": entities_to_action},
                    blocking=False,
                )
            else:
                _LOGGER.info(
                    "Acción %s (desde API=%s) para grupo %s: No se requieren cambios de estado.",
                    service_to_call,
                    api_state,
                    group,
                )

