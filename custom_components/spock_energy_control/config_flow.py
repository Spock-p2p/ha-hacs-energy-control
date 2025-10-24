from __future__ import annotations

from homeassistant import config_entries
import voluptuous as vol
from homeassistant.helpers import entity_registry as er, device_registry as dr
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_ENTITIES, CONF_API_TOKEN

SUPPORTED_DOMAINS = {
    "switch": "Switches",
    "light": "Luces",
    "fan": "Ventiladores",
    "climate": "Clima",
    "media_player": "Media Players",
}


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
        device_registry = dr.async_get(self.hass)

        grouped_entities: dict[str, str] = {}
        grouped_by_domain: dict[str, list[tuple[str, str]]] = {
            dom: [] for dom in SUPPORTED_DOMAINS.keys()
        }

        for ent in entity_registry.entities.values():
            if ent.domain not in SUPPORTED_DOMAINS:
                continue

            # --- Obtener nombre de dispositivo (más descriptivo) ---
            device_name = None
            if ent.device_id:
                device = device_registry.async_get(ent.device_id)
                if device:
                    device_name = device.name_by_user or device.name

            # --- Fallbacks de nombre ---
            friendly_name = (
                device_name
                or getattr(ent, "original_name", None)
                or getattr(ent, "name", None)
            )

            if not friendly_name:
                state = self.hass.states.get(ent.entity_id)
                if state and isinstance(state.attributes, dict):
                    friendly_name = state.attributes.get("friendly_name", ent.entity_id)
                else:
                    friendly_name = ent.entity_id

            grouped_by_domain[ent.domain].append((ent.entity_id, friendly_name))

        # --- Ordenar y agrupar ---
        for domain, entries in grouped_by_domain.items():
            if not entries:
                continue
            label_header = SUPPORTED_DOMAINS[domain]
            for entity_id, name in sorted(entries, key=lambda x: x[1].lower()):
                grouped_entities[entity_id] = f"{name} ({label_header})"

        schema = vol.Schema(
            {
                vol.Required(CONF_API_TOKEN): str,
                vol.Required(CONF_ENTITIES, default=[]): cv.multi_select(grouped_entities),
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
            return self.async_create_entry(title="", data=user_input)

        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)

        grouped_entities: dict[str, str] = {}
        grouped_by_domain: dict[str, list[tuple[str, str]]] = {
            dom: [] for dom in SUPPORTED_DOMAINS.keys()
        }

        for ent in entity_registry.entities.values():
            if ent.domain not in SUPPORTED_DOMAINS:
                continue

            device_name = None
            if ent.device_id:
                device = device_registry.async_get(ent.device_id)
                if device:
                    device_name = device.name_by_user or device.name

            friendly_name = (
                device_name
                or getattr(ent, "original_name", None)
                or getattr(ent, "name", None)
            )

            if not friendly_name:
                state = self.hass.states.get(ent.entity_id)
                if state and isinstance(state.attributes, dict):
                    friendly_name = state.attributes.get("friendly_name", ent.entity_id)
                else:
                    friendly_name = ent.entity_id

            grouped_by_domain[ent.domain].append((ent.entity_id, friendly_name))

        for domain, entries in grouped_by_domain.items():
            if not entries:
                continue
            label_header = SUPPORTED_DOMAINS[domain]
            for entity_id, name in sorted(entries, key=lambda x: x[1].lower()):
                grouped_entities[entity_id] = f"{name} ({label_header})"

        current = self.config_entry.options.get(
            CONF_ENTITIES, self.config_entry.data.get(CONF_ENTITIES, [])
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_ENTITIES, default=current): cv.multi_select(grouped_entities),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
