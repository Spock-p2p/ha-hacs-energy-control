import logging
from datetime import timedelta
import async_timeout
import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, ENDPOINT_URL, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class SpockEnergyCoordinator(DataUpdateCoordinator):
    """Coordinator que consulta el endpoint remoto y expone la acción."""

    def __init__(self, hass: HomeAssistant, api_token: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.hass = hass
        self._session = async_get_clientsession(hass)
        self.api_token = api_token

    async def _async_update_data(self):
        """Consultar el endpoint remoto con autenticación, seguro para cualquier hilo."""
        try:
            # Ejecutar la llamada HTTP dentro del event loop principal de Home Assistant
            data = await self.hass.async_add_executor_job(self._fetch_data)
        except Exception as err:
            raise UpdateFailed(f"HTTP error: {err}") from err

        action = (data or {}).get("action")
        if action not in ("start", "stop"):
            _LOGGER.debug("Respuesta sin acción válida: %s", data)
            return {"action": None}

        _LOGGER.debug("Acción recibida: %s", action)
        return {"action": action}

    def _fetch_data(self):
        """Función síncrona que realiza la llamada HTTP, ejecutada dentro del loop principal."""
        import requests  # uso seguro dentro de executor
        headers = {"X-Auth-Token": self.api_token}
        try:
            resp = requests.get(ENDPOINT_URL, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as err:
            _LOGGER.error("Error HTTP en SpockEnergyCoordinator: %s", err)
            raise err
