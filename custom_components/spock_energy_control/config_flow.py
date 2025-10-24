"""Config flow for Energy Control integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

# Ajusta el DOMAIN según tu manifest.json
from .const import DOMAIN 

_LOGGER = logging.getLogger(__name__)

# Dominios Soportados
DOMAINS_TO_FILTER = ["switch", "light", "fan", "climate", "media_player"]


# Constantes de configuración
CONF_API_TOKEN = "api_token"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_GREEN_DEVICES = "green_devices"
CONF_YELLOW_DEVICES = "yellow_devices"

# Esquema base para el formulario de configuración
DATA_SCHEMA = vol.Schema(
    {
        # CAMBIO: Añadido API Token como campo de contraseña
        vol.Required(CONF_API_TOKEN): selector.TextSelector(
            selector.TextSelectorConfig(type="password")
        ),
        # CAMBIO: Eliminado CONF_API_URL
        
        vol.Required(CONF_SCAN_INTERVAL, default=60): vol.All(vol.Coerce(int), vol.Range(min=10)),
        
        # Selector para Green Devices (SGReady)
        vol.Required(CONF_GREEN_DEVICES, default=[]): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=DOMAINS_TO_FILTER,
                multiple=True,
            )
        ),
        
        # Selector para Yellow Devices (SGReady)
        vol.Required(CONF_YELLOW_DEVICES, default=[]): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=DOMAINS_TO_FILTER,
                multiple=True,
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
            # 1. Validación de la exclusividad (sin cambios)
            green_devices = set(user_input.get(CONF_GREEN_DEVICES, []))
            yellow_devices = set(user_input.get(CONF_YELLOW_DEVICES, []))
            
            if green_devices.intersection(yellow_devices):
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
