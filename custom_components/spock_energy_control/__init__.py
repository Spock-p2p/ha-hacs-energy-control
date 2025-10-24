"""The Energy Control integration."""
from __future__ import annotations

import logging
import asyncio
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

# Importa las constantes del componente
from .const import DOMAIN

# Importa las constantes de configuración definidas en config_flow.py
from .config_flow import (
    CONF_API_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_GREEN_DEVICES,
    CONF_YELLOW_DEVICES,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = []
HARDCODED_API_URL = "https://flex.spock.es/api/status"


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Energy Control from a config entry."""
    config_data = {**entry.data, **entry.options}
    coordinator = EnergyControlCoordinator(hass, config_data)

    # Estructura por entry_id para poder cancelar el ticker al desinstalar
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "unsub": None,
    }

    # Listener para cambios de opciones
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Primer fetch (da tiempo a que acaben otros inits)
    await asyncio.sleep(2)
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.info("Energy Control iniciado: primer fetch realizado.")

    # Ticker manual (porque no hay entidades que escuchen al coordinator)
    interval = coordinator.update_interval or timedelta(seconds=60)

    async def _tick(_now):
        _LOGGER.debug("Energy Control tick → solicitando refresh…")
        await coordinator.async_request_refresh()

    unsub = async_track_time_interval(hass, _tick, interval)
    hass.data[DOMAIN][entry.entry_id]["unsub"] = unsub
    _LOGGER.info("Ciclo programado cada %s.", interval)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if entry_data and entry_data.get("unsub"):
        entry_data["unsub"]()  # cancelar el ticker
    return True


class EnergyControlCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator que consulta el endpoint y ejecuta acciones SGReady."""

    def __init__(self, hass: HomeAssistant, config: dict):
        """Initialize the coordinator."""
        # Propiedades
        self.config = config
        self.api_token: str = config[CONF_API_TOKEN]
        self.green_devices: list[str] = config.get(CONF_GREEN_DEVICES, [])
        self.yellow_devices: list[str] = config.get(CONF_YELLOW_DEVICES, [])
        self._session = async_get_clientsession(hass)

        _LOGGER.debug(
            "Listas de dispositivos cargadas: Green=%s, Yellow=%s",
            self.green_devices,
            self.yellow_devices,
        )

        # Intervalo
        scan_interval_seconds = 60
        try:
            scan_interval_seconds = int(config.get(CONF_SCAN_INTERVAL, 60))
            if scan_interval_seconds < 10:
                scan_interval_seconds = 10
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Valor de Scan Interval inválido (%s), usando 60 segundos por defecto",
                config.get(CONF_SCAN_INTERVAL),
            )
            scan_interval_seconds = 60

        update_interval = timedelta(seconds=scan_interval_seconds)

        _LOGGER.debug(
            "Coordinador inicializado. Intervalo de actualización: %s s",
            scan_interval_seconds,
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,  # lo reutilizamos para el ticker
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint and execute SGReady actions."""
        _LOGGER.debug("Fetching API data from %s", HARDCODED_API_URL)
        try:
            headers = {"X-Auth-Token": self.api_token}
            async with self._session.get(HARDCODED_API_URL, headers=headers) as response:
                if response.status == 403:
                    raise UpdateFailed("API Token inválido (Error 403 Forbidden)")
                if response.status != 200:
                    text = await response.text()
                    _LOGGER.error("API error %s: %s", response.status, text)
                    raise UpdateFailed(f"API returned status {response.status}")

                data = await response.json(content_type=None)

            if not isinstance(data, dict) or "green" not in data or "yellow" not in data:
                _LOGGER.error("API response format is incorrect: %s", data)
                raise UpdateFailed("API response format incorrect.")

            await self._execute_sgready_actions(data)
            return data

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except UpdateFailed:
            raise
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"An unexpected error occurred: {err}") from err

    async def _execute_sgready_actions(self, status_data: dict) -> None:
        """Ejecuta las acciones de encendido/apagado basadas en la respuesta SGReady."""
        _LOGGER.debug("SGReady status received: %s", status_data)

        device_groups = {
            "green": self.green_devices,
            "yellow": self.yellow_devices,
        }

        for device_type, state in status_data.items():
            devices_to_control = device_groups.get(device_type)
            if not devices_to_control:
                _LOGGER.debug(
                    "No devices configured for group '%s', skipping action.", device_type
                )
                continue

            service = None
            if state == "start":
                service = "turn_on"
            elif state == "stop":
                service = "turn_off"

            if service:
                _LOGGER.info(
                    "Executing SGReady action: %s for %s devices: %s",
                    service,
                    device_type,
                    devices_to_control,
                )
                await self.hass.services.async_call(
                    "homeassistant",
                    service,
                    {"entity_id": devices_to_control},
                    blocking=False,
                )
            else:
                _LOGGER.warning(
                    "Unknown state for %s devices: %s (Expected 'start' or 'stop')",
                    device_type,
                    state,
                )
