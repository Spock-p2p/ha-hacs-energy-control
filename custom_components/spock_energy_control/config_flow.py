"""Config flow for Spock Energy Control."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from aiohttp import ClientError

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigFlow, ConfigEntry, OptionsFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    # TextSelector, # <-- CAMBIO ELIMINADO
    # TextSelectorConfig, # <-- CAMBIO ELIMINADO
    # TextSelectorType, # <-- CAMBIO ELIMINADO
)
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_API_TOKEN,
    CONF_PLANT_ID, # <-- CAMBIO AÑADIDO
    CONF_GREEN_DEVICES,
    CONF_YELLOW_DEVICES,
    HARDCODED_API_URL,
    # CONF_TELEMETRY_URL, # <-- CAMBIO ELIMINADO
)

_LOGGER = logging.getLogger(__name__)


async def validate_auth(
    hass: HomeAssistant, api_token: str
) -> dict[str, str]:
    """Valida el API token haciendo una llamada al endpoint GET."""
    session = async_get_clientsession(hass)
    headers = {"X-Auth-Token": api_token}
    
    try:
        async with session.get(HARDCODED_API_URL, headers=headers, timeout=10) as resp:
            if resp.status == 403:
                return {"base": "invalid_auth"}
            resp.raise_for_status() 
            return {} 
            
    except (asyncio.TimeoutError, ClientError):
        return {"base": "cannot_connect"}
    except Exception:
        _LOGGER.exception("Error desconocido al validar API token")
        return {"base": "unknown"}


class SpockEnergyControlConfigFlow(ConfigFlow, domain=DOMAIN):
    """Maneja el flujo de configuración para Spock Energy Control."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Maneja el paso de configuración inicial (todos los campos)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            
            # Solo validamos el token. El plant_id no se puede validar.
            errors = await validate_auth(self.hass, user_input[CONF_API_TOKEN])
            
            if not errors:
                # Usamos una combinación de token y plant_id para el ID único
                unique_id = f"{user_input[CONF_API_TOKEN]}_{user_input[CONF_PLANT_ID]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title="Spock Energy Control",
                    data=user_input,
                )

        STEP_USER_DATA_SCHEMA = vol.Schema(
            {
                vol.Required(CONF_API_TOKEN): str,
                # --- CAMBIO: Añadido Plant ID, Eliminado Telemetry URL ---
                vol.Required(CONF_PLANT_ID): str,
                # --- FIN DEL CAMBIO ---
                vol.Optional(
                    CONF_GREEN_DEVICES,
                    default=[],
                ): EntitySelector(
                    EntitySelectorConfig(
                        multiple=True,
                        domain=["switch", "light", "input_boolean", "automation"]
                    )
                ),
                vol.Optional(
                    CONF_YELLOW_DEVICES,
                    default=[],
                ): EntitySelector(
                    EntitySelectorConfig(
                        multiple=True,
                        domain=["switch", "light", "input_boolean", "automation"]
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlowHandler:
        """Obtiene el flujo de opciones para esta entrada."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(OptionsFlow):
    """Maneja el flujo de opciones (reconfiguración y selección de dispositivos)."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Inicializa el flujo de opciones."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Maneja el paso inicial del flujo de opciones."""
        errors: dict[str, str] = {}
        
        current_config = {**self.config_entry.data, **self.config_entry.options}
        
        if user_input is not None:
            old_token = current_config.get(CONF_API_TOKEN)
            
            if user_input[CONF_API_TOKEN] != old_token:
                errors = await validate_auth(self.hass, user_input[CONF_API_TOKEN])
            
            if not errors:
                # Actualizamos el ID único si ha cambiado
                new_unique_id = f"{user_input[CONF_API_TOKEN]}_{user_input[CONF_PLANT_ID]}"
                if self.config_entry.unique_id != new_unique_id:
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, unique_id=new_unique_id
                    )
                
                return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_API_TOKEN,
                    default=current_config.get(CONF_API_TOKEN),
                ): str,
                # --- CAMBIO: Añadido Plant ID, Eliminado Telemetry URL ---
                vol.Required(
                    CONF_PLANT_ID,
                    default=current_config.get(CONF_PLANT_ID),
                ): str,
                # --- FIN DEL CAMBIO ---
                vol.Optional(
                    CONF_GREEN_DEVICES,
                    default=current_config.get(CONF_GREEN_DEVICES, []),
                ): EntitySelector(
                    EntitySelectorConfig(
                        multiple=True,
                        domain=["switch", "light", "input_boolean", "automation"]
                    )
                ),
                vol.Optional(
                    CONF_YELLOW_DEVICES,
                    default=current_config.get(CONF_YELLOW_DEVICES, []),
                ): EntitySelector(
                    EntitySelectorConfig(
                        multiple=True,
                        domain=["switch", "light", "input_boolean", "automation"]
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )
