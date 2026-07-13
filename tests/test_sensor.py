"""Unit tests for the OpenWindows sensor platform."""
from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)

from custom_components.openwindows.sensor import (
    CurrentOutdoorSensor,
    DegreesSavedSensor,
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
    assert attrs["reference_zone"] == "crossvent"
    assert attrs["humidity_gate_blocking"] is False
    assert attrs["ac_on"] is False


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
