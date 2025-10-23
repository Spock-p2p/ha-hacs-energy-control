from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON, STATE_OFF
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([EnergyControlSwitch(hass, entry)], True)

class EnergyControlSwitch(SwitchEntity):
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self._attr_name = "Spock Energy Control Active"
        self._attr_unique_id = "spock_energy_control_active"
        self._attr_is_on = True

    async def async_turn_on(self, **kwargs):
        self._attr_is_on = True
        self.hass.data[DOMAIN][self.entry.entry_id]["active"] = True
        await self.async_update_ha_state()

    async def async_turn_off(self, **kwargs):
        self._attr_is_on = False
        self.hass.data[DOMAIN][self.entry.entry_id]["active"] = False
        await self.async_update_ha_state()

    @property
    def is_on(self):
        return self._attr_is_on
