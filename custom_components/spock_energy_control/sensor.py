from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN
from . import SpockEnergyCoordinator  # Importar el coordinador desde init.py

_LOGGER = logging.getLogger(__name__)

# Definir los sensores que queremos crear
SENSOR_TYPES: tuple[tuple[str, str], ...] = (
    ("green", "Green Devices Status"),
    ("yellow", "Yellow Devices Status"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configura los sensores a partir de la entrada de configuración."""
    
    # Obtener el coordinador que ya está corriendo (creado en init.py)
    coordinator: SpockEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Crear una lista de entidades sensor
    entities_to_add = [
        SpockApiStatusSensor(coordinator, entry, data_key, name)
        for data_key, name in SENSOR_TYPES
    ]

    async_add_entities(entities_to_add, True)


class SpockApiStatusSensor(CoordinatorEntity[SpockEnergyCoordinator], SensorEntity):
    """Sensor que representa el estado (start/stop) de un grupo de dispositivos."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SpockEnergyCoordinator,
        entry: ConfigEntry,
        data_key: str,
        name: str,
    ) -> None:
        """Inicializa el sensor."""
        super().__init__(coordinator)  # Enlazar con el coordinador
        self._data_key = data_key
        
        # --- Atributos de la entidad ---
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{data_key}_status"

        # Icono dinámico
        self._attr_icon = "mdi:power-plug-off" # Icono por defecto
        
        # Agrupar los sensores en un solo "Dispositivo" en Home Assistant
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Spock Energy Control Status",
            manufacturer="Spock",
            model="API Status",
        )

    @property
    def native_value(self) -> str | None:
        """Devuelve el estado actual ('start' o 'stop') desde el coordinador."""
        if not self.coordinator.data:
            return None
        
        # Acceder a self.coordinator.data["green"] o self.coordinator.data["yellow"]
        return self.coordinator.data.get(self._data_key)

    @property
    def icon(self) -> str:
        """Devuelve un icono basado en el estado (el "semáforo" que querías)."""
        state = self.native_value
        if state == "start":
            # Verde
            return "mdi:power-plug"
        if state == "stop":
            # Rojo
            return "mdi:power-plug-off"
        
        # Desconocido
        return "mdi:help-rhombus-outline"
