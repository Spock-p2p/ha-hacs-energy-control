"""Constantes para la integración Spock Energy Control."""
from __future__ import annotations

DOMAIN = "spock_energy_control"

# --- Config Flow ---
CONF_API_TOKEN = "api_token"
CONF_PLANT_ID = "plant_id" 
CONF_GREEN_DEVICES = "green_devices"
CONF_YELLOW_DEVICES = "yellow_devices"

# --- Defaults ---
DEFAULT_SCAN_INTERVAL_S = 60

# --- Plataformas ---
PLATFORMS: list[str] = ["sensor", "switch"] 

# --- API ---
HARDCODED_API_URL = "https://flex.spock.es/api/status"
HARDCODED_API_URL_TELEMETRIA = "https://iot-ha.spock.es/api/iot_telemetry"
