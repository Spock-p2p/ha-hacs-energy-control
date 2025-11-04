"""Spock Energy Control (SGReady)"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant, State
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import entity_registry as er 
from homeassistant.helpers import device_registry as dr

from .const import (
    DOMAIN,
    CONF_API_TOKEN,
    CONF_PLANT_ID,
    CONF_GREEN_DEVICES,
    CONF_YELLOW_DEVICES,
    DEFAULT_SCAN_INTERVAL_S, 
    PLATFORMS,
    HARDCODED_API_URL,
    HARDCODED_API_URL_TELEMETRIA,
)

_LOGGER = logging.getLogger(__name__)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recarga la entrada de configuración."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura Spock Energy Control."""
    cfg = {**entry.data, **entry.options}
    
    coordinator = SpockEnergyCoordinator(hass, cfg, entry)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "run_actions": True,
    }

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await asyncio.sleep(2)
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.info("Spock Energy Control: primer fetch realizado.")

    _LOGGER.info(
         "Spock Energy Control: ciclo automático iniciado cada %s.", 
         coordinator.update_interval
    )
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descarga la entrada de configuración."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    
    return unload_ok


class SpockEnergyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator que consulta el endpoint y ejecuta acciones SGReady."""

    def __init__(self, hass: HomeAssistant, config: dict, entry: ConfigEntry) -> None: 
        """Inicializa el coordinador."""
        self.config = config
        self.config_entry = entry 
        self.api_token: str = config[CONF_API_TOKEN]
        self.plant_id: str = config[CONF_PLANT_ID] # <-- CAMBIO: Guardar plant_id
        self.green_devices: list[str] = config.get(CONF_GREEN_DEVICES, [])
        self.yellow_devices: list[str] = config.get(CONF_YELLOW_DEVICES, [])
        
        self.entity_registry: er.EntityRegistry = er.async_get(hass)
        self.device_registry: dr.DeviceRegistry = dr.async_get(hass) 
        self._power_sensor_entity_ids: set[str] | None = None
        
        self._session = async_get_clientsession(hass)

        seconds = DEFAULT_SCAN_INTERVAL_S
        _LOGGER.debug("Usando intervalo hardcoded de %s segundos", seconds)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=seconds),
        )

    def _find_power_sensors(self) -> set[str]:
        """Encuentra automáticamente los sensores de potencia."""
        if self._power_sensor_entity_ids is not None:
            return self._power_sensor_entity_ids 

        all_controlled_entities = self.green_devices + self.yellow_devices
        if not all_controlled_entities:
            self._power_sensor_entity_ids = set()
            return set()
        
        found_sensor_ids = set()
        processed_device_ids = set()

        for entity_id in all_controlled_entities:
            entry = self.entity_registry.async_get(entity_id)
            
            if not entry or not entry.device_id:
                continue
                
            device_id = entry.device_id
            
            if device_id in processed_device_ids:
                continue
            processed_device_ids.add(device_id)

            entities_on_device = er.async_entries_for_device(
                self.entity_registry, device_id
            )
            
            for device_entity in entities_on_device:
                if (
                    device_entity.domain == "sensor" and 
                    device_entity.device_class == "power"
                ):
                    _LOGGER.info(
                        "Sensor de potencia encontrado para el dispositivo '%s': %s",
                        device_id,
                        device_entity.entity_id
                    )
                    found_sensor_ids.add(device_entity.entity_id)

        self._power_sensor_entity_ids = found_sensor_ids
        return self._power_sensor_entity_ids


    async def _async_send_telemetry(self) -> None:
        """Envía telemetría para cada sensor de potencia detectado."""
        power_sensor_ids = self._find_power_sensors()
        if not power_sensor_ids:
            _LOGGER.debug("No se encontraron sensores de potencia asociados. Omitiendo telemetría.")
            return

        headers = {"X-Auth-Token": self.api_token}

        for sensor_id in power_sensor_ids:
            try:
                state: State | None = self.hass.states.get(sensor_id)
                if not state or state.state in ("unknown", "unavailable"):
                    _LOGGER.warning("No se pudo leer el sensor de potencia '%s'. Omitiendo.", sensor_id)
                    continue
                
                power_value = float(state.state)

                desc_device = "Dispositivo Desconocido"
                sensor_entry = self.entity_registry.async_get(sensor_id)
                
                if sensor_entry and sensor_entry.device_id:
                    device_entry = self.device_registry.async_get(sensor_entry.device_id)
                    if device_entry:
                        desc_device = device_entry.name_by_user or device_entry.name

                telemetry_data = {
                   "plant_id": self.plant_id,
                   "desc_device": desc_device,
                   "sensor_id": sensor_id,
                   "power": str(power_value),
                }

                _LOGGER.debug("Enviando telemetría para %s: %s", sensor_id, telemetry_data)
                
                async with self._session.post(
                    HARDCODED_API_URL_TELEMETRIA,
                    headers=headers, 
                    json=telemetry_data,
                    timeout=10
                ) as resp:
                    if resp.status >= 300:
                        _LOGGER.error(
                            "Error al enviar telemetría para %s (HTTP %s): %s",
                            sensor_id,
                            resp.status,
                            await resp.text()
                        )
                    else:
                        _LOGGER.debug("Telemetría enviada con éxito para %s", sensor_id)
            
            except Exception as err:
                _LOGGER.error("Error al procesar/enviar telemetría para %s: %s", sensor_id, err)


    async def _async_update_data(self) -> dict[str, Any]:
        """Obtiene los datos de la API (sensores) y ejecuta acciones."""
        _LOGGER.debug("Iniciando ciclo de actualización...")
        
        # 1. Enviar telemetría
        try:
            await self._async_send_telemetry()
        except Exception as e:
            _LOGGER.error("Error en _async_send_telemetry (no fatal): %s", e)

        # 2. Obtener estado SGReady
        _LOGGER.debug("Fetching API data (SGReady status) from %s", HARDCODED_API_URL)
        try:
            # --- CAMBIO: de .get a .post ---
            headers = {"X-Auth-Token": self.api_token}
            json_payload = {"plant_id": self.plant_id}
            
            async with self._session.post(
                HARDCODED_API_URL, 
                headers=headers, 
                json=json_payload
            ) as resp:
            # --- FIN DEL CAMBIO ---
                if resp.status == 403:
                    raise UpdateFailed("API Token o Plant ID inválido (403)")
                if resp.status != 200:
                    txt = await resp.text()
                    _LOGGER.error("API error %s: %s", resp.status, txt)
                    raise UpdateFailed(f"HTTP {resp.status}")

                data = await resp.json(content_type=None)

            if not isinstance(data, dict) or "green" not in data or "yellow" not in data:
                raise UpdateFailed(f"Formato de respuesta inesperado: {data}")

            await self._execute_sgready_actions(data)
            return data

        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Fetcher error: {err}") from err

    async def _execute_sgready_actions(self, status: dict) -> None:
        """Ejecuta las acciones on/off en los dispositivos."""
        entry_id = self.config_entry.entry_id
        run_actions = self.hass.data[DOMAIN].get(entry_id, {}).get("run_actions", True)
        
        if not run_actions:
            _LOGGER.debug("Acciones deshabilitadas por el interruptor. Omitiendo ejecución.")
            return

        groups = {"green": self.green_devices, "yellow": self.yellow_devices}
        
        for group, api_state in status.items():
            all_targets = groups.get(group) or []
            if not all_targets:
                _LOGGER.debug("Sin dispositivos en grupo %s; se omite.", group)
                continue

            service_to_call: str | None = None
            desired_state: str | None = None

            if api_state == "start":
                service_to_call = "turn_on"
                desired_state = "on"
            elif api_state == "stop":
                service_to_call = "turn_off"
                desired_state = "off"
            
            if not service_to_call or not desired_state:
                _LOGGER.warning("Estado desconocido para %s: %s", group, api_state)
                continue

            entities_to_action = []
            for entity_id in all_targets:
                try:
                    current_state_obj = self.hass.states.get(entity_id)

                    if not current_state_obj:
                        _LOGGER.warning(
                            "No se pudo encontrar el estado de la entidad '%s' (grupo %s). Se omitirá.", 
                            entity_id,
                            group
                        )
                        continue
                    
                    current_state = current_state_obj.state
                    if current_state != desired_state:
                        entities_to_action.append(entity_id)
                
                except Exception as e:
                    _LOGGER.error("Error al procesar entidad %s: %s", entity_id, e)

            if entities_to_action:
                _LOGGER.info(
                    "Acción %s (desde API=%s) para %s: %s", 
                    service_to_call, 
                    api_state, 
                    group, 
                    entities_to_action
                )
                await self.hass.services.async_call(
                    "homeassistant",
                    service_to_call,
                    {"entity_id": entities_to_action},
                    blocking=False,
                )
            else:
                _LOGGER.info(
                    "Acción %s (desde API=%s) para grupo %s: No se requieren cambios de estado.",
                    service_to_call,
                    api_state,
                    group
                )
