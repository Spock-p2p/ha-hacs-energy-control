from homeassistant import config_entries
import voluptuous as vol
from homeassistant.helpers import entity_registry as er
from homeassistant.components.homeassistant import DOMAIN as HA_DOMAIN
from .const import DOMAIN, CONF_ENTITIES

class EnergyControlFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Spock Energy Control", data=user_input)

        entity_registry = er.async_get(self.hass)
        valid_entities = []
        for e in entity_registry.entities.values():
            if e.domain in ("switch", "light", "fan", "climate", "media_player"):
                if any(x in e.entity_id.lower() for x in ["power", "energy", "consumption", "current"]):
                    valid_entities.append(e.entity_id)

        schema = vol.Schema({
            vol.Required(CONF_ENTITIES, default=[]): vol.All(vol.EnsureList(), [vol.In(valid_entities)])
        })

        return self.async_show_form(step_id="user", data_schema=schema)
