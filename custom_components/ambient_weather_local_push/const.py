"""Constants for Ambient Weather Local Push."""

DOMAIN = "ambient_weather_local_push"

CONF_NAME = "station_name"

ATTR_PASSKEY = "PASSKEY"
ATTR_MAC = "MAC"
ATTR_LAST_DATA = "last_data"
ATTR_KNOWN_SENSORS = "known_sensors"
ATTR_SENSOR_UPDATE_IN_PROGRESS = "sensor_update_in_progress"
ATTR_STATIONTYPE = "stationtype"
ATTR_LIGHTNING_DATA = "lightning_data"

STORAGE_KEY = f"{DOMAIN}_data"
STORAGE_VERSION = 1

IGNORED_WEBHOOK_KEYS = {
    "q",
    ATTR_PASSKEY,
    ATTR_MAC,
    ATTR_STATIONTYPE,
}
