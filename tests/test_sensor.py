"""Unit tests for the OpenWindows sensor platform."""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.util import dt as dt_util

from custom_components.openwindows.sensor import (
    CurrentOutdoorSensor,
    DegreesSavedSensor,
    NextAiringSensor,
    NextCloseSensor,
    NextOpenSensor,
    PredictedIndoorSensor,
    VerdictSensor,
    ZoneBureauSensor,
    ZoneCrossventSensor,
)


def test_verdict_sensor(fake_coordinator, fake_entry):
    entity = VerdictSensor(fake_coordinator(), fake_entry)
    assert entity.native_value == "keep_closed"
    assert entity.unique_id == "test_entry_verdict"
    attrs = entity.extra_state_attributes
    assert attrs["reason"] == "Indoor 27.5C above comfort but outdoor not cool enough yet"
    assert attrs["outdoor_temp"] == 30.0
    assert attrs["indoor_ref_temp"] == 27.5
    assert attrs["humidity_gate_blocking"] is False


def test_next_open_sensor(fake_coordinator, fake_entry):
    entity = NextOpenSensor(fake_coordinator(), fake_entry)
    assert entity.device_class == SensorDeviceClass.TIMESTAMP
    assert entity.native_value == datetime(2026, 7, 13, 20, 0, tzinfo=UTC)
    assert entity.unique_id == "test_entry_next_open"


def test_next_close_sensor(fake_coordinator, fake_entry):
    entity = NextCloseSensor(fake_coordinator(), fake_entry)
    assert entity.device_class == SensorDeviceClass.TIMESTAMP
    assert entity.native_value == datetime(2026, 7, 14, 7, 0, tzinfo=UTC)


def test_predicted_indoor_sensor(fake_coordinator, fake_entry):
    entity = PredictedIndoorSensor(fake_coordinator(), fake_entry)
    # Peak indoor_pred across the canned forecast series is 28.5.
    assert entity.native_value == 28.5
    assert entity.device_class == SensorDeviceClass.TEMPERATURE
    assert entity.state_class == SensorStateClass.MEASUREMENT
    assert entity.extra_state_attributes["forecast"] == entity.coordinator.data.forecast_series
    # "forecast" must be excluded from recorder history.
    assert "forecast" in PredictedIndoorSensor._unrecorded_attributes


def test_predicted_indoor_sensor_handles_empty_forecast(fake_coordinator, fake_entry):
    entity = PredictedIndoorSensor(fake_coordinator(forecast_series=[]), fake_entry)
    assert entity.native_value is None
    assert entity.extra_state_attributes["forecast"] == []


def test_current_outdoor_sensor(fake_coordinator, fake_entry):
    entity = CurrentOutdoorSensor(fake_coordinator(), fake_entry)
    assert entity.native_value == 30.0
    assert entity.device_class == SensorDeviceClass.TEMPERATURE
    assert entity.extra_state_attributes["dew_point"] == 16.5


def test_zone_crossvent_sensor(fake_coordinator, fake_entry):
    entity = ZoneCrossventSensor(fake_coordinator(), fake_entry)
    assert entity.native_value == "keep_closed"
    attrs = entity.extra_state_attributes
    assert attrs["indoor_temp"] == 27.5
    assert attrs["indoor_dew_point"] == 15.2
    assert attrs["humidity_gate_blocking"] is False


def test_zone_bureau_sensor(fake_coordinator, fake_entry):
    entity = ZoneBureauSensor(fake_coordinator(), fake_entry)
    assert entity.native_value == "open"
    attrs = entity.extra_state_attributes
    assert attrs["indoor_temp"] == 26.0
    assert attrs["indoor_dew_point"] == 14.0
    assert attrs["humidity_gate_blocking"] is False


def test_degrees_saved_sensor(fake_coordinator, fake_entry):
    entity = DegreesSavedSensor(fake_coordinator(), fake_entry)
    assert entity.native_value == 3.2
    assert entity.device_class == SensorDeviceClass.TEMPERATURE
    assert entity.state_class == SensorStateClass.MEASUREMENT


def test_next_airing_sensor(fake_entry):
    when = datetime(2026, 11, 2, 8, 0, tzinfo=UTC)
    scheduler = SimpleNamespace(next_airing=when, next_slot_key="morning")
    entity = NextAiringSensor(SimpleNamespace(airing_scheduler=scheduler), fake_entry)
    assert entity.device_class == SensorDeviceClass.TIMESTAMP
    assert entity.name == "Next Airing"
    assert entity.unique_id == "test_entry_next_airing"
    assert entity.should_poll is False
    assert entity.native_value == when
    assert entity.extra_state_attributes == {"slot": "morning"}

    scheduler.next_airing = None
    scheduler.next_slot_key = None
    assert entity.native_value is None
    assert entity.extra_state_attributes == {"slot": None}


async def test_next_airing_sensor_follows_mode(hass, freezer, loaded_entry):
    await hass.config.async_set_time_zone("Europe/Paris")
    freezer.move_to(datetime(2026, 11, 2, 6, 0, tzinfo=ZoneInfo("Europe/Paris")))
    _, coordinator = await loaded_entry()
    manager = coordinator.mode_manager

    await manager.async_set_override("force_cooling", dt_util.now())
    await hass.async_block_till_done()
    state = hass.states.get("sensor.openwindows_next_airing")
    assert state.state == "unknown"

    await manager.async_set_override("force_airing", dt_util.now())
    await hass.async_block_till_done()
    state = hass.states.get("sensor.openwindows_next_airing")
    assert state.state == "2026-11-02T07:00:00+00:00"
    assert state.attributes["slot"] == "morning"
