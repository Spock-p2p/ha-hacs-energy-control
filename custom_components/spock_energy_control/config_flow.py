"""Config flow for Energy Control integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

# Ajusta el DOMAIN según tu manifest.json
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Dominios Soportados (como en tu configuración original)
SUPPORTED_DOMAINS = {
    "switch": "Switches",
    "light": "Luces",
    "fan": "Ventiladores",
    "climate": "Clima",
    "media_player": "Media Players",
}

# Generar la lista de opciones para los selectores de entidades
ENTITY_SELECTOR_OPTIONS = [
    selector.EntityFilterSelectorConfig(domain=domain) 
    for domain in SUPPORTED_DOMAINS
]


# Nuevas constantes para la configuración
CONF_API_URL = "api_url"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_GREEN_DEVICES = "green_devices"
CONF_YELLOW_DEVICES = "yellow_devices"

# Esquema base para el formulario de configuración
DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_URL): str,
        vol.Required(CONF_SCAN_INTERVAL, default=60): vol.All(vol.Coerce(int), vol.Range(min=10)),
        
        # Selector para Green Devices (SGReady) - Usa todos los dominios
        vol.Required(CONF_GREEN_DEVICES, default=[]): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=ENTITY_SELECTOR_OPTIONS,
                multiple=True,
                translation_key=CONF_GREEN_DEVICES,
            )
        ),
        
        # Selector para Yellow Devices (SGReady) - Usa todos los dominios
        vol.Required(CONF_YELLOW_DEVICES, default=[]): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=ENTITY_SELECTOR_OPTIONS,
                multiple=True,
                translation_key=CONF_YELLOW_DEVICES,
            )
        ),
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Energy Control."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # 1. Validación de la exclusividad
            green_devices = set(user_input.get(CONF_GREEN_DEVICES, []))
            yellow_devices = set(user_input.get(CONF_YELLOW_DEVICES, []))
            
            # Comprobar si hay entidades seleccionadas en ambas listas
            if green_devices.intersection(yellow_devices):
                # Usaremos la clave de error 'exclusive_devices'
                errors["base"] = "exclusive_devices" 
            else:
                # 2. Si es válido, crear la entrada de configuración
                return self.async_create_entry(title="Energy Control", data=user_input)

        # 3. Mostrar el formulario
        return self.async_show_form(
            step_id="user", 
            data_schema=DATA_SCHEMA, 
            errors=errors
        )
