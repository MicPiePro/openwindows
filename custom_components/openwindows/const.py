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
