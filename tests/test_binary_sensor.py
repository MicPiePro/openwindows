"""Unit tests for the OpenWindows binary_sensor platform."""
from __future__ import annotations

from custom_components.openwindows.binary_sensor import (
    ACActiveBinarySensor,
    HumidityGateBinarySensor,
)


def test_ac_active_binary_sensor_off(fake_coordinator, fake_entry):
    entity = ACActiveBinarySensor(fake_coordinator(), fake_entry)
    assert entity.is_on is False
    assert entity.unique_id == "test_entry_ac_active"


def test_ac_active_binary_sensor_on(fake_coordinator, fake_entry):
    entity = ACActiveBinarySensor(fake_coordinator(ac_on=True), fake_entry)
    assert entity.is_on is True


def test_humidity_gate_binary_sensor_off(fake_coordinator, fake_entry):
    entity = HumidityGateBinarySensor(fake_coordinator(), fake_entry)
    assert entity.is_on is False
    assert entity.unique_id == "test_entry_humidity_gate"


def test_humidity_gate_binary_sensor_on(fake_coordinator, fake_entry):
    entity = HumidityGateBinarySensor(
        fake_coordinator(humidity_gate_blocking=True), fake_entry
    )
    assert entity.is_on is True
