import asyncio
import aiohttp
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.event import async_call_later
from .const import DOMAIN, ENDPOINT, CONF_ENTITIES, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry):
    """Set up the integration."""
    entities = entry.data.get(CONF_ENTITIES, [])
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "entities": entities,
        "active": True
    }

    async def poll_loop():
        _LOGGER.info("Spock Energy Control: poller iniciado.")
        while True:
            conf = hass.data[DOMAIN][entry.entry_id]
            if not conf["active"]:
                await asyncio.sleep(UPDATE_INTERVAL)
                continue
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(ENDPOINT) as resp:
                        data = await resp.json()
                        action = data.get("action")
                        _LOGGER.debug(f"Spock Energy Control: respuesta {data}")
                        if action == "stop":
                            for eid in entities:
                                await hass.services.async_call("homeassistant", "turn_off", {"entity_id": eid})
                            _LOGGER.info(f"Apagadas entidades: {entities}")
                        elif action == "start":
                            for eid in entities:
                                await hass.services.async_call("homeassistant", "turn_on", {"entity_id": eid})
                            _LOGGER.info(f"Encendidas entidades: {entities}")
            except Exception as e:
                _LOGGER.warning(f"Error consultando endpoint: {e}")
            await asyncio.sleep(UPDATE_INTERVAL)

    hass.loop.create_task(poll_loop())
    return True
