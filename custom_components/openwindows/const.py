"""Constants for the OpenWindows integration."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "openwindows"
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=15)

# --- Config-entry DATA keys (structural, chosen in ConfigFlow -> entry.data) ---
CONF_WEATHER = "weather"
CONF_CROSSVENT_TEMP = "crossvent_temp_sensors"
CONF_CROSSVENT_HUM = "crossvent_humidity_sensors"
CONF_BUREAU_TEMP = "bureau_temp_sensor"
CONF_BUREAU_HUM = "bureau_humidity_sensor"
CONF_DOOR = "door_sensor"
CONF_ORIENTATION = "orientation"

# --- OPTIONS keys (tuning, OptionsFlow -> entry.options) ---
CONF_COMFORT_TARGET = "comfort_target"
CONF_OPEN_MARGIN = "open_margin"
CONF_CLOSE_MARGIN = "close_margin"
CONF_MIN_INDOOR = "min_indoor"
CONF_HUMIDITY_GATE = "humidity_gate_enabled"
CONF_MAX_DEWPOINT = "max_outdoor_dewpoint"
CONF_WALL_MASS = "wall_mass"
CONF_VENTILATION = "ventilation"
CONF_UPDATE_INTERVAL = "update_interval_min"

# --- OPTIONS defaults ---
DEFAULT_COMFORT_TARGET = 25.0
DEFAULT_OPEN_MARGIN = 2.0
DEFAULT_CLOSE_MARGIN = 0.3
DEFAULT_MIN_INDOOR = 23.0
DEFAULT_HUMIDITY_GATE = True
DEFAULT_MAX_DEWPOINT = 18.0
DEFAULT_WALL_MASS = "medium"
DEFAULT_VENTILATION = "high"
DEFAULT_UPDATE_INTERVAL_MIN = 15

# --- Enumerations ---
WALL_MASS_OPTIONS = ["light", "medium", "heavy"]
VENT_OPTIONS = ["low", "medium", "high"]
ORIENTATION_OPTIONS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

# --- Verdicts ---
VERDICT_OPEN = "open"
VERDICT_CLOSE = "close"
VERDICT_KEEP_CLOSED = "keep_closed"
VERDICT_OPEN_SOON = "open_soon"
VERDICT_INACTIVE = "inactive"

# --- Modes (kept in sync by value with mode.py) ---
MODE_COOLING = "cooling"
MODE_AIRING = "airing"
OVERRIDE_AUTO = "auto"
OVERRIDE_FORCE_COOLING = "force_cooling"
OVERRIDE_FORCE_AIRING = "force_airing"
OVERRIDE_OPTIONS = [OVERRIDE_AUTO, OVERRIDE_FORCE_COOLING, OVERRIDE_FORCE_AIRING]
WEEKDAY_OPTIONS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# --- Mode OPTIONS keys ---
CONF_WARM_SEASON_START = "warm_season_start"
CONF_WARM_SEASON_END = "warm_season_end"
CONF_HEAT_THRESHOLD = "heat_threshold"
CONF_HEAT_END_THRESHOLD = "heat_end_threshold"
CONF_HEAT_END_DAYS = "heat_end_days"
CONF_MORNING_ENABLED = "morning_enabled"
CONF_MORNING_TIME = "morning_time"
CONF_MORNING_DAYS = "morning_days"
CONF_MORNING_ROOMS = "morning_rooms"
CONF_OFFICE_ENABLED = "office_enabled"
CONF_OFFICE_TIME = "office_time"
CONF_OFFICE_DAYS = "office_days"
CONF_OFFICE_ROOMS = "office_rooms"

# --- Mode OPTIONS defaults ---
DEFAULT_WARM_SEASON_START = "04-01"
DEFAULT_WARM_SEASON_END = "10-31"
DEFAULT_HEAT_THRESHOLD = 28.0
DEFAULT_HEAT_END_THRESHOLD = 25.0
DEFAULT_HEAT_END_DAYS = 2
DEFAULT_MORNING_ENABLED = True
DEFAULT_MORNING_TIME = "08:00:00"
DEFAULT_MORNING_DAYS = list(WEEKDAY_OPTIONS)
DEFAULT_MORNING_ROOMS = "Chambre et salon"
DEFAULT_OFFICE_ENABLED = True
DEFAULT_OFFICE_TIME = "09:20:00"
DEFAULT_OFFICE_DAYS = ["mon", "tue", "wed", "thu", "fri"]
DEFAULT_OFFICE_ROOMS = "Bureau"
DEFAULT_OVERRIDE_DAYS = 1
