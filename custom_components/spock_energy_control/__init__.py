"""The Energy Control integration."""
from __future__ import annotations

import logging
from datetime import timedelta
import json

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

# Importa las constantes del componente
from .const import DOMAIN 

# Importa las constantes de configuración definidas en config_flow.py
from .config_flow import (
    CONF_API_TOKEN,
    CONF_SCAN_INTERVAL, 
    CONF_GREEN_DEVICES, 
    CONF_YELLOW_DEVICES
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
    
    # Almacena el coordinador en hass.data PRIMERO
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Registra el "listener" para la reconfiguración
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    
    # AHORA, ejecuta el primer refresh
    await coordinator.async_config_entry_first_refresh()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id)
    return True


class EnergyControlCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """My custom coordinator."""

    def __init__(self, hass: HomeAssistant, config: dict):
        """Initialize my coordinator."""
        
        # --- CAMBIO ---
        # Define todas las propiedades de la clase PRIMERO
        self.hass = hass
        self.config = config
        self.api_token = config[CONF_API_TOKEN]
        self.green_devices: list[str] = config.get(CONF_GREEN_DEVICES, [])
        self.yellow_devices: list[str] = config.get(CONF_YELLOW_DEVICES, [])
        
        _LOGGER.debug(
            "Listas de dispositivos cargadas en coordinador: Green=%s, Yellow=%s",
            self.green_devices,
            self.yellow_devices
        )
        
        # Calcula el intervalo de actualización
        scan_interval_seconds = 60 # Default
        try:
            scan_interval_seconds = int(config.get(CONF_SCAN_INTERVAL, 60))
            if scan_interval_seconds < 10:
                scan_interval_seconds = 10
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Valor de Scan Interval inválido (%s), usando 60 segundos por defecto",
                config.get(CONF_SCAN_INTERVAL)
            )
            scan_interval_seconds = 60
        
        update_interval = timedelta(seconds=scan_interval_seconds)
        
        _LOGGER.debug(
            "Coordinador inicializado. Intervalo de actualización: %s segundos",
            scan_interval_seconds
        )

        # --- CAMBIO ---
        # Llama a super().__init__ AL FINAL, una vez que todo esté definido
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )


    async def _async_update_data(self) -> dict[str, str]:
        """Fetch data from API endpoint and execute SGReady actions."""
        _LOGGER.debug("Fetching API data from %s", HARDCODED_API_URL)
        try:
            headers = {"X-Auth-Token": self.api_token}
            async with aiohttp.ClientSession() as session:
                async with session.get(HARDCODED_API_URL, headers=headers) as response:
                    
                    if response.status == 403:
                         raise UpdateFailed("API Token inválido (Error 403 Forbidden)")
                    if response.status != 200:
                        response_text = await response.text()
                        _LOGGER.error("API error %s: %s", response.status, response_text)
                        raise UpdateFailed(f"API returned status {response.status}")
                    
                    data = await response.json(content_type=None)
                    
                    if not isinstance(data, dict) or "green" not in data or "yellow" not in data:
                         _LOGGER.error("API response format is incorrect: %s", data)
                         raise UpdateFailed("API response format isC incorrect.")

            await self._execute_sgready_actions(data)
            return data
            
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
        except Exception as err:
            if isinstance(err, UpdateFailed):
                raise
            raise UpdateFailed(f"An unexpected error occurred: {err}")

    async def _execute_sgready_actions(self, status_data: dict):
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
                    devices_to_control
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
                    state
                )
