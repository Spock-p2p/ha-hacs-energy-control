"""Config flow for Spock Energy Control."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.config_entries import ConfigFlow, ConfigEntry, OptionsFlow
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
)

from .const import (
    DOMAIN,
    CONF_API_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_GREEN_DEVICES,
    CONF_YELLOW_DEVICES,
    CONF_PLANT_ID,
    CONF_EMS_TOKEN,
)

_LOGGER = logging.getLogger(__name__)


class SpockConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Spock Energy Control."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # (Aqui puedes añadir validacion de API)
            await self.async_set_unique_id(user_input[CONF_API_TOKEN])
            self._abort_if_unique_id_configured()

            # Guardamos todo en entry.data
            return self.async_create_entry(
                title="Spock Energy Control", 
                data=user_input
            )

        # --- INICIO DE LA MODIFICACIÓN ---
        # Ahora el schema inicial pide TODO
        schema = vol.Schema({
            vol.Required(CONF_API_TOKEN): str,
            
            # --- SECCIÓN 1: SGReady ---
            vol.Marker("sgready_section"): str, 
            
            vol.Optional(CONF_SCAN_INTERVAL, default=60):
                vol.All(vol.Coerce(int), vol.Range(min=10)),
            
            vol.Optional(CONF_GREEN_DEVICES, default=[]):
                EntitySelector(EntitySelectorConfig(domain=["switch", "climate"], multiple=True)),
            
            vol.Optional(CONF_YELLOW_DEVICES, default=[]):
                EntitySelector(EntitySelectorConfig(domain=["switch", "climate"], multiple=True)),
                
            # --- SECCIÓN 2: Spock EMS ---
            vol.Marker("ems_section"): str, 
            
            vol.Optional(CONF_PLANT_ID, default=""): 
                str,
            
            vol.Optional(CONF_EMS_TOKEN, default=""): 
                str,
        })
        # --- FIN DE LA MODIFICACIÓN ---

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
            # Al guardar, se guarda en entry.options
            return self.async_create_entry(title="", data=user_input)

        # --- INICIO DE LA MODIFICACIÓN ---
        # El OptionsFlow ahora lee la configuracion actual 
        # (sea de .data o de .options) y la muestra para editar.
        
        # El API Token no se puede editar, asi que no lo incluimos
        
        config = {**self.config_entry.data, **self.config_entry.options}

        options_schema = vol.Schema({
            # --- SECCIÓN 1: SGReady ---
            vol.Marker("sgready_section"): str, 
            
            vol.Optional(CONF_SCAN_INTERVAL, default=config.get(CONF_SCAN_INTERVAL, 60)):
                vol.All(vol.Coerce(int), vol.Range(min=10)),
            
            vol.Optional(CONF_GREEN_DEVICES, default=config.get(CONF_GREEN_DEVICES, [])):
                EntitySelector(EntitySelectorConfig(domain=["switch", "climate"], multiple=True)),
            
            vol.Optional(CONF_YELLOW_DEVICES, default=config.get(CONF_YELLOW_DEVICES, [])):
                EntitySelector(EntitySelectorConfig(domain=["switch", "climate"], multiple=True)),
                
            # --- SECCIÓN 2: Spock EMS ---
            vol.Marker("ems_section"): str, 
            
            vol.Optional(CONF_PLANT_ID, description={"suggested_value": config.get(CONF_PLANT_ID, "")}): 
                str,
            
            vol.Optional(CONF_EMS_TOKEN, description={"suggested_value": config.get(CONF_EMS_TOKEN, "")}): 
                str,
        })
        # --- FIN DE LA MODIFICACIÓN ---

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema
        )
