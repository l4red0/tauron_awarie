"""Constants for the Tauron Awarie integration."""

DOMAIN = "tauron_awarie"

# Configuration keys (stored in config entry)
CONF_CITY_GAID = "city_gaid"
CONF_PROVINCE_GAID = "province_gaid"
CONF_DISTRICT_GAID = "district_gaid"
CONF_COMMUNE_GAID = "commune_gaid"
CONF_CITY_AREA_ID = "city_area_id"
CONF_CITY_NAME = "city_name"
CONF_COMMUNE_NAME = "commune_name"
CONF_DISTRICT_NAME = "district_name"
CONF_PROVINCE_NAME = "province_name"
CONF_CREATE_CALENDAR = "create_calendar"
CONF_CALENDAR_ENTITY = "calendar_entity"

# Tauron WAAPI
TAURON_BASE_URL = "https://www.tauron-dystrybucja.pl"
TAURON_OUTAGES_URL = f"{TAURON_BASE_URL}/waapi/outages/area"

# Sensor attributes
ATTR_NEXT_START = "next_start"
ATTR_NEXT_END = "next_end"
ATTR_NEXT_MESSAGE = "next_message"
ATTR_NEXT_TYPE = "next_type"
ATTR_OUTAGE_COUNT = "outage_count"
ATTR_OUTAGES = "outages"
ATTR_ATTRIBUTION = "attribution"

ATTRIBUTION = "Data provided by TAURON Dystrybucja"

# TypeId from Tauron WAAPI response
OUTAGE_TYPE = {
    1: "Planowane",
    2: "Awaryjne",
}

# Fetch range for outages query
FETCH_RANGE_DAYS = 7
