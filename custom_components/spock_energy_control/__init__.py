from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
# si ya tienes estos imports, mantén los tuyos:
from .config_flow import (
    CONF_API_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_GREEN_DEVICES,
    CONF_YELLOW_DEVICES,
)

_LOGGER = logging.getLogger(__name__)

HARDCODED_API_URL = "https://flex.spock.es/api/status"


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Spock Energy Control."""
    cfg = {**entry.data, **entry.options}
    coordinator = SpockEnergyCoordinator(hass, cfg)

    # Estructura por entry_id (guardamos también el unsub del ticker)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "unsub": None,
    }

    # Reactivar al cambiar opciones
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Primer fetch y programación del ciclo
    await asyncio.sleep(2)
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.info("Spock Energy Control: primer fetch realizado.")

    interval = coordinator.update_interval or timedelta(seconds=60)

    async def _tick(_now):
        try:
            _LOGGER.debug("Spock Energy Control tick → async_request_refresh()")
            await coordinator.async_request_refresh()
        except Exception as exc:  # noqa: BLE001
            _LOGGER.exception("Tick error: %s", exc)

    unsub = async_track_time_interval(hass, _tick, interval)
    hass.data[DOMAIN][entry.entry_id]["unsub"] = unsub
    _LOGGER.info("Spock Energy Control: ciclo programado cada %s.", interval)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    entry_data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if entry_data and entry_data.get("unsub"):
        entry_data["unsub"]()  # cancelar ticker
    return True


class SpockEnergyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator que consulta el endpoint y ejecuta acciones SGReady."""

    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        self.config = config
        self.api_token: str = config[CONF_API_TOKEN]
        self.green_devices: list[str] = config.get(CONF_GREEN_DEVICES, [])
        self.yellow_devices: list[str] = config.get(CONF_YELLOW_DEVICES, [])
        self._session = async_get_clientsession(hass)

        # Intervalo desde opciones (mínimo 10s)
        seconds = 60
        try:
            seconds = max(10, int(config.get(CONF_SCAN_INTERVAL, 60)))
        except Exception:
            pass

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=seconds),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        _LOGGER.debug("Fetching API data from %s", HARDCODED_API_URL)
        try:
            headers = {"X-Auth-Token": self.api_token}
            async with self._session.get(HARDCODED_API_URL, headers=headers) as resp:
                if resp.status == 403:
                    raise UpdateFailed("API Token inválido (403)")
                if resp.status != 200:
                    txt = await resp.text()
                    _LOGGER.error("API error %s: %s", resp.status, txt)
                    raise UpdateFailed(f"HTTP {resp.status}")

                data = await resp.json(content_type=None)

            # Validación mínima
            if not isinstance(data, dict) or "green" not in data or "yellow" not in data:
                raise UpdateFailed(f"Formato de respuesta inesperado: {data}")

            await self._execute_sgready_actions(data)
            return data

        except UpdateFailed:
            raise
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Fetcher error: {err}") from err

    async def _execute_sgready_actions(self, status: dict) -> None:
        groups = {"green": self.green_devices, "yellow": self.yellow_devices}
        for group, state in status.items():
            targets = groups.get(group) or []
            if not targets:
                _LOGGER.debug("Sin dispositivos en grupo %s; se omite.", group)
                continue

            service = "turn_on" if state == "start" else "turn_off" if state == "stop" else None
            if not service:
                _LOGGER.warning("Estado desconocido para %s: %s", group, state)
                continue

            _LOGGER.info("Acción %s para %s: %s", service, group, targets)
            await self.hass.services.async_call(
                "homeassistant",
                service,
                {"entity_id": targets},
                blocking=False,
            )
