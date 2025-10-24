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

# --- CAMBIO ---
# Hemos vaciado la lista de plataformas, ya que no vamos a crear 
# una entidad de sensor, solo a controlar otras entidades.
PLATFORMS: list[Platform] = []

# URL Fija de la API
HARDCODED_API_URL = "https://flex.spock.es/api/status"


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

    # --- CAMBIO ---
    # Hemos eliminado la carga de plataformas, ya que la lista está vacía.
    # await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # --- CAMBIO ---
    # Modificado para reflejar que no hay plataformas que descargar.
    # Simplemente eliminamos los datos del coordinador.
    hass.data[DOMAIN].pop(entry.entry_id)
    return True


class EnergyControlCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """My custom coordinator."""

    def __init__(self, hass: HomeAssistant, config: dict):
        """Initialize my coordinator."""
        self.config = config
        
        # Obtener el API Token de la configuración
        self.api_token = config[CONF_API_TOKEN]
        
        # Inicialización de listas de dispositivos
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
            # El servidor espera 'X-Auth-Token', no 'Authorization: Bearer'
            headers = {"X-Auth-Token": self.api_token}

            async with aiohttp.ClientSession() as session:
                
                async with session.get(HARDCODED_API_URL, headers=headers) as response:
                    
                    if response.status == 403: # Error de autorización (Forbidden)
                         raise UpdateFailed(f"API Token inválido (Error 403 Forbidden)")
                    if response.status != 200:
                        response_text = await response.text()
                        _LOGGER.error("API error %s: %s", response.status, response_text)
                        raise UpdateFailed(f"API returned status {response.status}")
                    
                    # Dejamos content_type=None para ignorar el 'text/html'
                    data = await response.json(content_type=None)
                    
                    if not isinstance(data, dict) or "green" not in data or "yellow" not in data:
                         _LOGGER.error("API response format is incorrect: %s", data)
                         raise UpdateFailed("API response format is incorrect.")

            # Procesa la respuesta y ejecuta acciones SGReady
            await self._execute_sgready_actions(data)
            
            return data
            
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
        except Exception as err:
            # Captura el error original si es uno de los que ya hemos lanzado
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
                
                # Llamar al servicio de Home Assistant para el grupo de dispositivos
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
