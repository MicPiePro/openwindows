"""Tests for the OpenWindows constants module."""
from datetime import timedelta

from custom_components.openwindows import const


def test_core_identifiers():
    assert const.DOMAIN == "openwindows"
    assert [p.value for p in const.PLATFORMS] == ["sensor", "binary_sensor"]
    assert const.DEFAULT_UPDATE_INTERVAL == timedelta(minutes=15)


def test_data_keys():
    assert const.CONF_WEATHER == "weather"
    assert const.CONF_CROSSVENT_TEMP == "crossvent_temp_sensors"
    assert const.CONF_CROSSVENT_HUM == "crossvent_humidity_sensors"
    assert const.CONF_BUREAU_TEMP == "bureau_temp_sensor"
    assert const.CONF_BUREAU_HUM == "bureau_humidity_sensor"
    assert const.CONF_DOOR == "door_sensor"
    assert const.CONF_ORIENTATION == "orientation"


def test_option_keys_and_defaults():
    assert const.CONF_COMFORT_TARGET == "comfort_target"
    assert const.DEFAULT_COMFORT_TARGET == 25.0
    assert const.CONF_OPEN_MARGIN == "open_margin"
    assert const.DEFAULT_OPEN_MARGIN == 2.0
    assert const.CONF_CLOSE_MARGIN == "close_margin"
    assert const.DEFAULT_CLOSE_MARGIN == 0.3
    assert const.CONF_MIN_INDOOR == "min_indoor"
    assert const.DEFAULT_MIN_INDOOR == 23.0
    assert const.CONF_HUMIDITY_GATE == "humidity_gate_enabled"
    assert const.DEFAULT_HUMIDITY_GATE is True
    assert const.CONF_MAX_DEWPOINT == "max_outdoor_dewpoint"
    assert const.DEFAULT_MAX_DEWPOINT == 18.0
    assert const.CONF_WALL_MASS == "wall_mass"
    assert const.DEFAULT_WALL_MASS == "medium"
    assert const.CONF_VENTILATION == "ventilation"
    assert const.DEFAULT_VENTILATION == "high"
    assert const.CONF_UPDATE_INTERVAL == "update_interval_min"
    assert const.DEFAULT_UPDATE_INTERVAL_MIN == 15


def test_enumerations_and_verdicts():
    assert const.WALL_MASS_OPTIONS == ["light", "medium", "heavy"]
    assert const.VENT_OPTIONS == ["low", "medium", "high"]
    assert const.ORIENTATION_OPTIONS == ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    assert const.VERDICT_OPEN == "open"
    assert const.VERDICT_CLOSE == "close"
    assert const.VERDICT_KEEP_CLOSED == "keep_closed"
    assert const.VERDICT_OPEN_SOON == "open_soon"
