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
    # CAMBIO: Eliminado CONF_API_URL
    CONF_API_TOKEN, # CAMBIO: Añadido
    CONF_SCAN_INTERVAL, 
    CONF_GREEN_DEVICES, 
    CONF_YELLOW_DEVICES
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# CAMBIO: URL Fija de la API
HARDCODED_API_URL = "http://flex.spock.es/api/status"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Energy Control from a config entry."""

    coordinator = EnergyControlCoordinator(hass, entry.data)
    
    coordinator.green_devices = entry.data.get(CONF_GREEN_DEVICES, [])
    coordinator.yellow_devices = entry.data.get(CONF_YELLOW_DEVICES, [])

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class EnergyControlCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """My custom coordinator."""

    def __init__(self, hass: HomeAssistant, config: dict):
        """Initialize my coordinator."""
        self.config = config
        
        # CAMBIO: Obtener el API Token de la configuración
        self.api_token = config[CONF_API_TOKEN]
        # CAMBIO: Eliminada la self.api_url

        self.green_devices: list[str] = []
        self.yellow_devices: list[str] = []

        update_interval = timedelta(seconds=config[CONF_SCAN_INTERVAL])

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict[str, str]:
        """Fetch data from API endpoint and execute SGReady actions."""
        try:
            # CAMBIO: Preparar la cabecera de autenticación
            headers = {"Authorization": f"Bearer {self.api_token}"}

            async with aiohttp.ClientSession() as session:
                
                # CAMBIO: Usar la URL fija y los headers
                async with session.get(HARDCODED_API_URL, headers=headers) as response:
                    
                    if response.status == 401: # Error de autorización
                         raise UpdateFailed(f"API Token inválido o caducado (Error 401)")
                    if response.status != 200:
                        raise UpdateFailed(f"API returned status {response.status}")
                    
                    data = await response.json()
                    
                    if not isinstance(data, dict) or "green" not in data or "yellow" not in data:
                         _LOGGER.error("API response format is incorrect: %s", data)
                         raise UpdateFailed("API response format is incorrect.")

            # Procesa la respuesta y ejecuta acciones (sin cambios)
            await self._execute_sgready_actions(data)
            
            return data
            
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
        except Exception as err:
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
