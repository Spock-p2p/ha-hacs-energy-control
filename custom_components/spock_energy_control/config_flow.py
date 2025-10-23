from __future__ import annotations

from homeassistant import config_entries
import voluptuous as vol
from homeassistant.helpers import entity_registry as er
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_ENTITIES


SUPPORTED_DOMAINS = ("switch", "light", "fan", "climate", "media_player")


class SpockEnergyControlFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Flujo de configuración inicial."""
        if user_input is not None:
            return self.async_create_entry(
                title="Spock Energy Control",
                data=user_input,
            )

        entity_registry = er.async_get(self.hass)
        valid_entities: list[str] = []

        for ent in entity_registry.entities.values():
            if ent.domain in SUPPORTED_DOMAINS:
                valid_entities.append(ent.entity_id)

        schema = vol.Schema(
            {
                vol.Required(CONF_ENTITIES, default=[]): cv.multi_select(valid_entities),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    def async_get_options_flow(config_entry):
        return SpockEnergyControlOptionsFlow(config_entry)


class SpockEnergyControlOptionsFlow(config_entries.OptionsFlow):
    """Permite editar entidades después de instalar la integración."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # Guardar en options (no sobreescribimos data)
            return self.async_create_entry(title="", data=user_input)

        entity_registry = er.async_get(self.hass)
        valid_entities: list[str] = []
        for ent in entity_registry.entities.values():
            if ent.domain in SUPPORTED_DOMAINS:
                valid_entities.append(ent.entity_id)

        current = self.config_entry.options.get(
            CONF_ENTITIES, self.config_entry.data.get(CONF_ENTITIES, [])
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_ENTITIES, default=current): cv.multi_select(
                    valid_entities
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)
