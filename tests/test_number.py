"""Tests for the override duration number entity."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

ENTITY = "number.openwindows_override_days"


async def test_override_days_set(hass, freezer, loaded_entry):
    await hass.config.async_set_time_zone("Europe/Paris")
    freezer.move_to(datetime(2026, 11, 2, 6, 0, tzinfo=ZoneInfo("Europe/Paris")))
    _, coordinator = await loaded_entry()

    state = hass.states.get(ENTITY)
    assert state.state == "1"
    assert state.attributes["min"] == 1
    assert state.attributes["max"] == 14
    assert state.attributes["step"] == 1
    assert state.attributes["unit_of_measurement"] == "d"
    assert state.attributes["mode"] == "box"

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": ENTITY, "value": 5},
        blocking=True,
    )
    assert coordinator.mode_manager.override_days == 5
    assert hass.states.get(ENTITY).state == "5"
