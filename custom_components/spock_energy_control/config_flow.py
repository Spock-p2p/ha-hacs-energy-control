"""Config flow for Spock Energy Control."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.config_entries import ConfigFlow, ConfigEntry, OptionsFlow
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectOption,
    EntitySelector,
    EntitySelectorConfig,
)
from homeassistant.const import CONF_API_TOKEN, CONF_SCAN_INTERVAL

# --- INICIO DE LA MODIFICACIÓN ---
# Importar las nuevas constantes desde const.py
from .const import DOMAIN, CONF_PLANT_ID, CONF_EMS_TOKEN
# --- FIN DE LA MODIFICACIÓN ---


_LOGGER = logging.getLogger(__name__)

# Constants defined in config_flow.py (following existing pattern)
CONF_GREEN_DEVICES = "green_devices"
CONF_YELLOW_DEVICES = "yellow_devices"


class SpockConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Spock Energy Control."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # Aquí deberías añadir la validación del API Token
            # Por ahora, simplemente lo aceptamos.
            # (En el futuro, aquí podrías llamar a la API con el token
            # y si devuelve 403, mostrar errors["base"] = "invalid_auth")
            
            await self.async_set_unique_id(user_input[CONF_API_TOKEN])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="Spock Energy Control", 
                data=user_input
            )

        # Esquema para el paso inicial (solo API Token)
        schema = vol.Schema({
            vol.Required(CONF_API_TOKEN): str,
        })

        return self.async_show_form(
            step_id="user", 
            data_schema=schema, 
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(OptionsFlow):
    """Handle an options flow for Spock Energy Control."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Guardar las opciones (incluyendo las nuevas de EMS)
            return self.async_create_entry(title="", data=user_input)

        # --- INICIO DE LA MODIFICACIÓN ---
        # Cargar los valores actuales (o los defaults)
        options = self.config_entry.options
        
        green_devices = options.get(CONF_GREEN_DEVICES, [])
        yellow_devices = options.get(CONF_YELLOW_DEVICES, [])
        scan_interval = options.get(CONF_SCAN_INTERVAL, 60)
        
        # Cargar los nuevos valores opcionales de EMS
        plant_id = options.get(CONF_PLANT_ID, "")
        ems_token = options.get(CONF_EMS_TOKEN, "")

        # Definir el esquema para el formulario de opciones
        options_schema = vol.Schema({
            # --- SECCIÓN SGReady (existente) ---
            vol.Optional(CONF_SCAN_INTERVAL, default=scan_interval):
                vol.All(vol.Coerce(int), vol.Range(min=10)),
            
            vol.Optional(CONF_GREEN_DEVICES, default=green_devices):
                EntitySelector(EntitySelectorConfig(domain=["switch", "climate"], multiple=True)),
            
            vol.Optional(CONF_YELLOW_DEVICES, default=yellow_devices):
                EntitySelector(EntitySelectorConfig(domain=["switch", "climate"], multiple=True)),
                
            # --- SECCIÓN Spock EMS (nueva) ---
            # Esto crea un título de sección
            vol.Marker("ems_section"): str, 
            
            # Nuevos campos opcionales
            vol.Optional(CONF_PLANT_ID, description={"suggested_value": plant_id}): 
                str,
            
            vol.Optional(CONF_EMS_TOKEN, description={"suggested_value": ems_token}): 
                str,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema
        )
        # --- FIN DE LA MODIFICACIÓN ---
