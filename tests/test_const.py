"""Tests for the OpenWindows constants module."""
from datetime import timedelta

from custom_components.openwindows import const, mode


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


def test_mode_constants_match_pure_module():
    assert const.VERDICT_INACTIVE == mode.VERDICT_INACTIVE
    assert const.MODE_COOLING == mode.MODE_COOLING
    assert const.MODE_AIRING == mode.MODE_AIRING
    assert const.OVERRIDE_OPTIONS == ["auto", "force_cooling", "force_airing"]
    assert const.WEEKDAY_OPTIONS == ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def test_mode_option_keys_and_defaults():
    assert const.CONF_WARM_SEASON_START == "warm_season_start"
    assert const.DEFAULT_WARM_SEASON_START == "04-01"
    assert const.CONF_WARM_SEASON_END == "warm_season_end"
    assert const.DEFAULT_WARM_SEASON_END == "10-31"
    assert (const.CONF_HEAT_THRESHOLD, const.DEFAULT_HEAT_THRESHOLD) == (
        "heat_threshold",
        28.0,
    )
    assert (const.CONF_HEAT_END_THRESHOLD, const.DEFAULT_HEAT_END_THRESHOLD) == (
        "heat_end_threshold",
        25.0,
    )
    assert (const.CONF_HEAT_END_DAYS, const.DEFAULT_HEAT_END_DAYS) == ("heat_end_days", 2)
    assert const.CONF_MORNING_ENABLED == "morning_enabled"
    assert const.DEFAULT_MORNING_ENABLED is True
    assert const.CONF_MORNING_TIME == "morning_time"
    assert const.DEFAULT_MORNING_TIME == "08:00:00"
    assert const.CONF_MORNING_DAYS == "morning_days"
    assert const.DEFAULT_MORNING_DAYS == const.WEEKDAY_OPTIONS
    assert const.CONF_MORNING_ROOMS == "morning_rooms"
    assert const.DEFAULT_MORNING_ROOMS == "Chambre et salon"
    assert const.CONF_OFFICE_ENABLED == "office_enabled"
    assert const.DEFAULT_OFFICE_ENABLED is True
    assert const.CONF_OFFICE_TIME == "office_time"
    assert const.DEFAULT_OFFICE_TIME == "09:20:00"
    assert const.CONF_OFFICE_DAYS == "office_days"
    assert const.DEFAULT_OFFICE_DAYS == ["mon", "tue", "wed", "thu", "fri"]
    assert const.CONF_OFFICE_ROOMS == "office_rooms"
    assert const.DEFAULT_OFFICE_ROOMS == "Bureau"
    assert const.DEFAULT_OVERRIDE_DAYS == 1
