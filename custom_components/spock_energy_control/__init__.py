import logging
from typing import Any
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import Platform

from .const import (
    DOMAIN,
    CONF_ENTITIES,
    CONF_API_TOKEN,
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
    entities = entry.options.get(CONF_ENTITIES, entry.data.get(CONF_ENTITIES, []))
    api_token = entry.data.get(CONF_API_TOKEN)
    if not api_token:
        _LOGGER.error("No se ha configurado ningún API token. Cancela la instalación.")
        return False

    coordinator = SpockEnergyCoordinator(hass, api_token)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_ACTIVE: True,
        DATA_ENTITIES: entities,
        DATA_UNSUB: None,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # --- Ciclo de comprobación (thread-safe) ---
    async def _tick(now):
        cfg = hass.data[DOMAIN][entry.entry_id]
        if not cfg[DATA_ACTIVE]:
            return

        coordinator = cfg["coordinator"]
        await coordinator.async_request_refresh()
        action = (coordinator.data or {}).get("action")
        if not action:
            return

        target_entities = cfg[DATA_ENTITIES]
        if not target_entities:
            _LOGGER.debug("No hay entidades seleccionadas.")
            return

        if action == "stop":
            _LOGGER.info("Apagando entidades: %s", target_entities)
            await hass.services.async_call(
                "homeassistant",
                "turn_off",
                {"entity_id": target_entities},
                blocking=False,
            )
        elif action == "start":
            _LOGGER.info("Encendiendo entidades: %s", target_entities)
            await hass.services.async_call(
                "homeassistant",
                "turn_on",
                {"entity_id": target_entities},
                blocking=False,
            )

    def _safe_tick(now):
        """Ejecutar el tick dentro del hilo principal, compatible con futuras versiones."""
        try:
            # Home Assistant 2025.4+ (nuevo método)
            hass.async_create_background_task(_tick(now), "spock_energy_control_tick")
        except AttributeError:
            # Compatibilidad con versiones anteriores
            hass.loop.call_soon_threadsafe(hass.async_create_task, _tick(now))

    unsub = async_track_time_interval(
        hass, _safe_tick, timedelta(seconds=UPDATE_INTERVAL_SECONDS)
    )
    hass.data[DOMAIN][entry.entry_id][DATA_UNSUB] = unsub

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
