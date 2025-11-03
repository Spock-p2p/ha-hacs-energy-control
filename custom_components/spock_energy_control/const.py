"""Constants for the Spock Energy Control integration."""
from __future__ import annotations
from datetime import timedelta

DOMAIN = "spock_energy_control"

# Configuration keys
CONF_API_TOKEN = "api_token"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_GREEN_DEVICES = "green_devices"
CONF_YELLOW_DEVICES = "yellow_devices"

# Defaults
DEFAULT_SCAN_INTERVAL_S = 60

# API
HARDCODED_API_URL = "https://flex.spock.es/api/status"
