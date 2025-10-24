from __future__ import annotations

from homeassistant import config_entries
import voluptuous as vol
from homeassistant.helpers import (
    entity_registry as er,
    device_registry as dr,
    area_registry as ar,
)
import homeassistant.helpers.config_validation as cv
import re

from .const import DOMAIN, CONF_ENTITIES, CONF_API_TOKEN

SUPPORTED_DOMAINS = {
    "switch": "Switches",
    "light": "Luces",
    "fan": "Ventiladores",
    "climate": "Clima",
    "media_player": "Media Players",
}

IGNORE_PATTERNS = re.compile(
    r"(tamper|motion|watermark|get_hacs|pre_release|debug|video|tracking)",
    re.IGNORECASE,
)


class SpockEnergyControlFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Flujo de configuración inicial."""
        if user_input is not None:
            return self.async_create_entry(title="Spock Energy Control", data=user_input)

        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)
        area_registry = ar.async_get(self.hass)

        grouped_entities: dict[str, str] = {}
        grouped_by_domain: dict[str, list[tuple[str, str]]] = {dom: [] for dom in SUPPORTED_DOMAINS}

        # --- Recorrer entidades ---
        for ent in entity_registry.entities.values():
            if ent.domain not in SUPPORTED_DOMAINS:
                continue
            if IGNORE_PATTERNS.search(ent.entity_id):
                continue

            device_name = None
            area_name = None

            if ent.device_id:
                device = device_registry.async_get(ent.device_id)
                if device:
                    device_name = device.name_by_user or device.name
                    if device.area_id:
                        area = area_registry.async_get(device.area_id)
                        if area:
                            area_name = area.name

            friendly_name = (
                device_name
                or getattr(ent, "original_name", None)
                or getattr(ent, "name", None)
            )

            if not friendly_name:
                state = self.hass.states.get(ent.entity_id)
                if state and isinstance(state.attributes, dict):
                    friendly_name = state.attributes.get("friendly_name")

            if not friendly_name:
                clean_name = ent.entity_id.split(".")[-1].replace("_", " ").title()
                friendly_name = clean_name

            domain_label = SUPPORTED_DOMAINS.get(ent.domain, ent.domain.capitalize())
            parts = [domain_label, friendly_name]
            if area_name:
                parts.append(area_name)
            display_name = " - ".join(parts)

            grouped_by_domain[ent.domain].append((ent.entity_id, display_name))

        # --- Añadir encabezados visuales ---
        ordered_list: list[tuple[str, str]] = []
        for domain, entries in grouped_by_domain.items():
            if not entries:
                continue
            label = SUPPORTED_DOMAINS[domain]
            # Encabezado visual
            ordered_list.append((f"header_{domain}", f"──── {label} ────"))
            # Entidades ordenadas
            for entity_id, name in sorted(entries, key=lambda x: x[1].lower()):
                ordered_list.append((entity_id, name))

        # Convertir a dict para el schema
        grouped_entities = {k: v for k, v in ordered_list if not k.startswith("header_")}

        # Multi-select no permite headers, así que los insertamos visualmente con caracteres
        visual_entities = {}
        for key, label in ordered_list:
            if key.startswith("header_"):
                visual_entities[f"__{key}__"] = label
            else:
                visual_entities[key] = f"   {label}"

        schema = vol.Schema(
            {
                vol.Required(CONF_API_TOKEN): str,
                vol.Required(CONF_ENTITIES, default=[]): cv.multi_select(visual_entities),
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
        area_registry = ar.async_get(self.hass)

        grouped_entities: dict[str, str] = {}
        grouped_by_domain: dict[str, list[tuple[str, str]]] = {dom: [] for dom in SUPPORTED_DOMAINS}

        for ent in entity_registry.entities.values():
            if ent.domain not in SUPPORTED_DOMAINS:
                continue
            if IGNORE_PATTERNS.search(ent.entity_id):
                continue

            device_name = None
            area_name = None

            if ent.device_id:
                device = device_registry.async_get(ent.device_id)
                if device:
                    device_name = device.name_by_user or device.name
                    if device.area_id:
                        area = area_registry.async_get(device.area_id)
                        if area:
                            area_name = area.name

            friendly_name = (
                device_name
                or getattr(ent, "original_name", None)
                or getattr(ent, "name", None)
            )

            if not friendly_name:
                state = self.hass.states.get(ent.entity_id)
                if state and isinstance(state.attributes, dict):
                    friendly_name = state.attributes.get("friendly_name")

            if not friendly_name:
                clean_name = ent.entity_id.split(".")[-1].replace("_", " ").title()
                friendly_name = clean_name

            domain_label = SUPPORTED_DOMAINS.get(ent.domain, ent.domain.capitalize())
            parts = [domain_label, friendly_name]
            if area_name:
                parts.append(area_name)
            display_name = " - ".join(parts)

            grouped_by_domain[ent.domain].append((ent.entity_id, display_name))

        ordered_list: list[tuple[str, str]] = []
        for domain, entries in grouped_by_domain.items():
            if not entries:
                continue
            label = SUPPORTED_DOMAINS[domain]
            ordered_list.append((f"header_{domain}", f"──── {label} ────"))
            for entity_id, name in sorted(entries, key=lambda x: x[1].lower()):
                ordered_list.append((entity_id, name))

        visual_entities = {}
        for key, label in ordered_list:
            if key.startswith("header_"):
                visual_entities[f"__{key}__"] = label
            else:
                visual_entities[key] = f"   {label}"

        current = self.config_entry.options.get(
            CONF_ENTITIES, self.config_entry.data.get(CONF_ENTITIES, [])
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_ENTITIES, default=current): cv.multi_select(visual_entities),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
