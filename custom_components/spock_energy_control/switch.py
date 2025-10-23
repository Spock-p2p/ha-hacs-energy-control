from __future__ import annotations
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DATA_ACTIVE, SWITCH_UNIQUE_ID, SWITCH_NAME

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([SpockEnergyControlSwitch(hass, entry)], True)


class SpockEnergyControlSwitch(SwitchEntity):
    _attr_has_entity_name = False
    _attr_name = SWITCH_NAME
    _attr_unique_id = SWITCH_UNIQUE_ID

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

    @property
    def is_on(self) -> bool:
        cfg = self.hass.data[DOMAIN][self.entry.entry_id]
        return bool(cfg[DATA_ACTIVE])

    async def async_turn_on(self, **kwargs: Any) -> None:
        cfg = self.hass.data[DOMAIN][self.entry.entry_id]
        cfg[DATA_ACTIVE] = True
        _LOGGER.info("Spock Energy Control: ACTIVADO")
        await self.async_update_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        cfg = self.hass.data[DOMAIN][self.entry.entry_id]
        cfg[DATA_ACTIVE] = False
        _LOGGER.info("Spock Energy Control: PAUSADO")
        await self.async_update_ha_state()
