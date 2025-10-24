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
# (Asegúrate de que estas constantes existen en config_flow.py como en el código anterior)
from .config_flow import (
    CONF_API_URL, 
    CONF_SCAN_INTERVAL, 
    CONF_GREEN_DEVICES, 
    CONF_YELLOW_DEVICES
)

_LOGGER = logging.getLogger(__name__)

# La plataforma principal del componente, si es necesario, si no, puedes eliminar.
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Energy Control from a config entry."""

    # 1. Inicializar el coordinador y pasar la configuración
    coordinator = EnergyControlCoordinator(hass, entry.data)
    
    # 2. Guardar las listas de dispositivos en el coordinador
    coordinator.green_devices = entry.data.get(CONF_GREEN_DEVICES, [])
    coordinator.yellow_devices = entry.data.get(CONF_YELLOW_DEVICES, [])

    # 3. Solicitar la primera actualización
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # 4. Establecer las plataformas (ej. sensor)
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
        self.api_url = config[CONF_API_URL]
        
        # Inicialización de listas de dispositivos para ser llenadas en async_setup_entry
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
            # 1. Realizar la llamada a la API
            async with aiohttp.ClientSession() as session:
                # Asegurarse de usar un protocolo si no está en la configuración (ej. http://)
                full_url = self.api_url if "://" in self.api_url else f"http://{self.api_url}"
                
                # Ejemplo de URL: http://flex.spock.es/api/status
                async with session.get(full_url) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"API returned status {response.status}")
                    
                    data = await response.json()
                    
                    # Verificar el formato de la respuesta (ej. {"green": "start", "yellow": "stop"})
                    if not isinstance(data, dict) or "green" not in data or "yellow" not in data:
                         _LOGGER.error("API response format is incorrect: %s", data)
                         raise UpdateFailed("API response format is incorrect.")

            # 2. Procesa la respuesta y ejecuta acciones SGReady
            await self._execute_sgready_actions(data)
            
            return data
            
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
        except Exception as err:
            raise UpdateFailed(f"An unexpected error occurred: {err}")

    async def _execute_sgready_actions(self, status_data: dict):
        """Ejecuta las acciones de encendido/apagado basadas en la respuesta SGReady."""
        
        _LOGGER.debug("SGReady status received: %s", status_data)
        
        # Mapeo de los tipos SGReady a las listas de dispositivos
        device_groups = {
            "green": self.green_devices,
            "yellow": self.yellow_devices,
        }
        
        # Iterar sobre los tipos (green, yellow) en la respuesta
        for device_type, state in status_data.items():
            devices_to_control = device_groups.get(device_type)
            
            # Solo si la lista de dispositivos está configurada Y no está vacía
            if not devices_to_control:
                continue
            
            # Determinar el servicio a llamar
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
                
                # 3. Llamar al servicio de Home Assistant para el grupo de dispositivos
                await self.hass.services.async_call(
                    "homeassistant",
                    service,  # "turn_on" o "turn_off"
                    {"entity_id": devices_to_control}, # La clave entity_id acepta una lista
                    blocking=False,
                )
            else:
                _LOGGER.warning(
                    "Unknown state for %s devices: %s (Expected 'start' or 'stop')", 
                    device_type, 
                    state
                )
