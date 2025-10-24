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

def _get_schema(config_data: dict[str, Any]) -> vol.Schema:
    """Genera el esquema de Voluptuous basado en la configuración existente."""
    return vol.Schema(
        {
            vol.Required(
                CONF_API_TOKEN, 
                default=config_data.get(CONF_API_TOKEN, "")
            ): selector.TextSelector(selector.TextSelectorConfig(type="password")),
            
            vol.Required(
                CONF_SCAN_INTERVAL, 
                default=config_data.get(CONF_SCAN_INTERVAL, 60)
            ): vol.All(vol.Coerce(int), vol.Range(min=10)),
            
            vol.Required(
                CONF_GREEN_DEVICES, 
                default=config_data.get(CONF_GREEN_DEVICES, [])
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain=DOMAINS_TO_FILTER, multiple=True)),
            
            vol.Required(
                CONF_YELLOW_DEVICES, 
                default=config_data.get(CONF_YELLOW_DEVICES, [])
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain=DOMAINS_TO_FILTER, multiple=True)),
        }
    )

def _validate_input(user_input: dict[str, Any]) -> dict[str, str]:
    """Valida la exclusividad de los dispositivos."""
    errors: dict[str, str] = {}
    green_devices = set(user_input.get(CONF_GREEN_DEVICES, []))
    yellow_devices = set(user_input.get(CONF_YELLOW_DEVICES, []))
    
    if green_devices.intersection(yellow_devices):
        errors["base"] = "exclusive_devices"
    return errors


# --- CAMBIO ---
# Añadimos config_entries.OptionsFlow para manejar la reconfiguración
class ConfigFlow(config_entries.ConfigFlow, config_entries.OptionsFlow, domain=DOMAIN):
    """Handle a config flow for Energy Control."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step (instalación)."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            errors = _validate_input(user_input)
            if not errors:
                return self.async_create_entry(title="Energy Control", data=user_input)

        # Muestra el formulario por primera vez
        return self.async_show_form(
            step_id="user", 
            data_schema=_get_schema({}), # Schema vacío para la primera vez
            errors=errors
        )

    # --- CAMBIO ---
    # Esta es la nueva función que maneja la reconfiguración
    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow (reconfiguración)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = _validate_input(user_input)
            if not errors:
                # Guarda la nueva configuración en las "opciones"
                return self.async_create_entry(title="", data=user_input)

        # Carga la configuración actual (opciones o datos) para pre-rellenar el formulario
        config_data = {**self.config_entry.data, **self.config_entry.options}

        return self.async_show_form(
            step_id="options",
            data_schema=_get_schema(config_data), # Schema pre-rellenado
            errors=errors,
        )
