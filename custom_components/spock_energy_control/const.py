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

#token api
CONF_API_TOKEN = "api_token"

# const para el sensor
PLATFORMS: list[str] = ["sensor"]

CONF_PLANT_ID = "plant_id"
CONF_EMS_TOKEN = "ems_token"
