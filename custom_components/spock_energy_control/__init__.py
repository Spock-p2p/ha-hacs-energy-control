import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import Platform
from datetime import timedelta

from .const import (
    DOMAIN,
    CONF_ENTITIES,
    DATA_ACTIVE,
    DATA_ENTITIES,
    DATA_UNSUB,
    UPDATE_INTERVAL_SECONDS,
)
from .coordinator import SpockEnergyCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SWITCH]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configurar integración desde la UI."""
    # Entidades configuradas: preferimos options (si existen) sobre data
    entities = entry.options.get(CONF_ENTITIES, entry.data.get(CONF_ENTITIES, []))

    api_token = entry.data.get("api_token")
    
    # Estado inicial: activo
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_ACTIVE: True,
        DATA_ENTITIES: entities,
        DATA_UNSUB: None,
        "coordinator": SpockEnergyCoordinator(hass, api_token),
    }

    # Iniciar coordinator (primera lectura)
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    await coordinator.async_config_entry_first_refresh()

    # Registrar plataformas (switch virtual)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Programar el ciclo de comprobación en intervalos
    def _tick(now):
        cfg = hass.data[DOMAIN][entry.entry_id]
        if not cfg[DATA_ACTIVE]:
            # Pausado: no consumimos red
            return

        coordinator = cfg["coordinator"]

        async def _act():
            await coordinator.async_request_refresh()
            action = (coordinator.data or {}).get("action")
            if not action:
                return

            target_entities = cfg[DATA_ENTITIES]
            if not target_entities:
                _LOGGER.debug("No hay entidades seleccionadas.")
                return

            # Ejecutar acción
            if action == "stop":
                _LOGGER.info("Apagando entidades: %s", target_entities)
                await hass.services.async_call(
                    "homeassistant", "turn_off", {"entity_id": target_entities}, blocking=False
                )
            elif action == "start":
                _LOGGER.info("Encendiendo entidades: %s", target_entities)
                await hass.services.async_call(
                    "homeassistant", "turn_on", {"entity_id": target_entities}, blocking=False
                )

        hass.async_create_task(_act())

    unsub = async_track_time_interval(
        hass, _tick, timedelta(seconds=UPDATE_INTERVAL_SECONDS)
    )
    hass.data[DOMAIN][entry.entry_id][DATA_UNSUB] = unsub

    # Escuchar cambios en opciones para recargar entidades al vuelo
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    _LOGGER.info(
        "Spock Energy Control listo. Entidades: %s. Intervalo: %ss",
        entities,
        UPDATE_INTERVAL_SECONDS,
    )
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Actualizar lista de entidades si cambian las opciones desde la UI."""
    cfg = hass.data[DOMAIN][entry.entry_id]
    new_entities = entry.options.get(CONF_ENTITIES, entry.data.get(CONF_ENTITIES, []))
    cfg[DATA_ENTITIES] = new_entities
    _LOGGER.info("Actualizadas entidades seleccionadas: %s", new_entities)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Desinstalar integración."""
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    cfg = hass.data[DOMAIN].pop(entry.entry_id, None)
    if cfg and cfg.get(DATA_UNSUB):
        cfg[DATA_UNSUB]()  # cancelar intervalo

    return ok
