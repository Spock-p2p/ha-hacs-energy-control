import logging
from datetime import timedelta

import async_timeout
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
        self._session = async_get_clientsession(hass)
        self.api_token = api_token  # <- aquí sin guion bajo, para mantenerlo simple y consistente

    async def _async_update_data(self):
        """Consultar el endpoint remoto con autenticación."""
        try:
            async with async_timeout.timeout(10):
                headers = {"X-Auth-Token": self.api_token}
                async with self._session.get(ENDPOINT_URL, headers=headers) as resp:
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)
        except Exception as err:
            raise UpdateFailed(f"HTTP error: {err}") from err

        action = (data or {}).get("action")
        if action not in ("start", "stop"):
            _LOGGER.debug("Respuesta sin acción válida: %s", data)
            return {"action": None}

        _LOGGER.debug("Acción recibida: %s", action)
        return {"action": action}
