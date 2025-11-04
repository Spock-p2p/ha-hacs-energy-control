"""Switch para habilitar/deshabilitar las acciones de Spock Energy Control."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configura el interruptor desde la entrada de configuración."""
    
    # No necesitamos el coordinator, solo acceso a hass.data
    async_add_entities([SpockActionsSwitch(hass, entry)])


class SpockActionsSwitch(SwitchEntity):
    """Interruptor para controlar la ejecución de acciones SGReady."""

    _attr_has_entity_name = True
    _attr_translation_key = "sgready_actions" # Usará los archivos de traducción
    _attr_icon = "mdi:auto-fix" # Icono de "magia" o "auto"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Inicializa el interruptor."""
        self.hass = hass
        self._entry_id = entry.entry_id
        
        # ID único para el interruptor
        self._attr_unique_id = f"{self._entry_id}_actions_enabled"
        
        # Asocia este interruptor al mismo dispositivo que los sensores
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="Spock Energy Control",
            manufacturer="Spock",
            model="SGReady Control",
        )

    @property
    def is_on(self) -> bool:
        """Devuelve true si las acciones están habilitadas."""
        # Lee el estado desde hass.data, con un default por si acaso
        return self.hass.data[DOMAIN].get(self._entry_id, {}).get("run_actions", True)

    async def async_turn_on(self, **kwargs) -> None:
        """Habilita la ejecución de acciones."""
        _LOGGER.debug("Habilitando acciones SGReady")
        self.hass.data[DOMAIN][self._entry_id]["run_actions"] = True
        self.async_write_state_changed() # Actualiza el estado en HA

    async def async_turn_off(self, **kwargs) -> None:
        """Deshabilita la ejecución de acciones."""
        _LOGGER.debug("Deshabilitando acciones SGReady")
        self.hass.data[DOMAIN][self._entry_id]["run_actions"] = False
        self.async_write_state_changed() # Actualiza el estado en HA
