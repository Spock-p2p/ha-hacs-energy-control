"""Spock Energy Control (SGReady)"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_API_TOKEN,
    CONF_GREEN_DEVICES,
    CONF_YELLOW_DEVICES,
    DEFAULT_SCAN_INTERVAL_S, 
    PLATFORMS,
    HARDCODED_API_URL,
)

_LOGGER = logging.getLogger(__name__)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recarga la entrada de configuración."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura Spock Energy Control."""
    cfg = {**entry.data, **entry.options}
    
    coordinator = SpockEnergyCoordinator(hass, cfg, entry) # <-- CAMBIO: Pasamos 'entry'

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "run_actions": True,  # <-- CAMBIO: Estado inicial del interruptor
    }

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await asyncio.sleep(2)
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.info("Spock Energy Control: primer fetch realizado.")

    _LOGGER.info(
         "Spock Energy Control: ciclo automático iniciado cada %s.", 
         coordinator.update_interval
    )
    
    # Esto cargará 'sensor.py' y el nuevo 'switch.py'
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descarga la entrada de configuración."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    
    return unload_ok


class SpockEnergyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator que consulta el endpoint y ejecuta acciones SGReady."""

    # CAMBIO: Añadimos 'entry' al __init__
    def __init__(self, hass: HomeAssistant, config: dict, entry: ConfigEntry) -> None: 
        """Inicializa el coordinador."""
        self.config = config
        self.config_entry = entry # Guardamos la entry
        self.api_token: str = config[CONF_API_TOKEN]
        self.green_devices: list[str] = config.get(CONF_GREEN_DEVICES, [])
        self.yellow_devices: list[str] = config.get(CONF_YELLOW_DEVICES, [])
        self._session = async_get_clientsession(hass)

        seconds = DEFAULT_SCAN_INTERVAL_S
        _LOGGER.debug("Usando intervalo hardcoded de %s segundos", seconds)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=seconds),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Obtiene los datos de la API (sensores) y ejecuta acciones."""
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

            if not isinstance(data, dict) or "green" not in data or "yellow" not in data:
                raise UpdateFailed(f"Formato de respuesta inesperado: {data}")

            # Los sensores se actualizan. Ahora, ejecutar acciones (si está habilitado)
            await self._execute_sgready_actions(data)
            return data

        except UpdateFailed:
            raise
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Fetcher error: {err}") from err

    async def _execute_sgready_actions(self, status: dict) -> None:
        """Ejecuta las acciones on/off en los dispositivos."""
        
        # --- CAMBIO: Comprobar si las acciones están habilitadas ---
        entry_id = self.config_entry.entry_id
        run_actions = self.hass.data[DOMAIN].get(entry_id, {}).get("run_actions", True)
        
        if not run_actions:
            _LOGGER.debug("Acciones deshabilitadas por el interruptor. Omitiendo ejecución.")
            return
        # --- FIN DEL CAMBIO ---

        groups = {"green": self.green_devices, "yellow": self.yellow_devices}
        
        for group, api_state in status.items():
            all_targets = groups.get(group) or []
            if not all_targets:
                _LOGGER.debug("Sin dispositivos en grupo %s; se omite.", group)
                continue

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

            entities_to_action = []
            for entity_id in all_targets:
                try:
                    current_state_obj = self.hass.states.get(entity_id)

                    if not current_state_obj:
                        _LOGGER.warning(
                            "No se pudo encontrar el estado de la entidad '%s' (grupo %s). Se omitirá.", 
                            entity_id,
                            group
                        )
                        continue
                    
                    current_state = current_state_obj.state
                    if current_state != desired_state:
                        entities_to_action.append(entity_id)
                
                except Exception as e:
                    _LOGGER.error("Error al procesar entidad %s: %s", entity_id, e)

            if entities_to_action:
                _LOGGER.info(
                    "Acción %s (desde API=%s) para %s: %s", 
                    service_to_call, 
                    api_state, 
                    group, 
                    entities_to_action
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
                    group
                )
