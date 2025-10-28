"""Constants for the Spock Energy Control integration."""

DOMAIN = "spock_energy_control"

CONF_ENTITIES = "entities"

# Polling
UPDATE_INTERVAL_SECONDS = 15

# Endpoint fijo (no configurable)
ENDPOINT_URL = "https://flex.spock.es/api/status"

# Datos en hass.data
DATA_ACTIVE = "active"
DATA_ENTITIES = "entities"
DATA_UNSUB = "unsub"

# Switch virtual
SWITCH_UNIQUE_ID = "spock_energy_control_active"
SWITCH_NAME = "Spock Energy Control Active"

# --- Constantes de Configuracion ---
CONF_API_TOKEN = "api_token"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_GREEN_DEVICES = "green_devices"
CONF_YELLOW_DEVICES = "yellow_devices"
CONF_PLANT_ID = "plant_id"
CONF_EMS_TOKEN = "ems_token"

# const para el sensor
PLATFORMS: list[str] = ["sensor"]
