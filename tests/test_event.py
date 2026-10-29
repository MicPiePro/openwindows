"""Tests for the airing reminder event entity."""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from homeassistant.components.event import EventEntity
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.openwindows.event import AiringReminderEvent

PARIS = ZoneInfo("Europe/Paris")


def test_event_entity_definition(fake_entry):
    entity = AiringReminderEvent(SimpleNamespace(airing_scheduler=None), fake_entry)
    assert isinstance(entity, EventEntity)
    assert entity.unique_id == "test_entry_airing_reminder"
    assert entity.name == "Airing Reminder"
    assert entity.event_types == ["morning", "office"]
    assert entity.should_poll is False
    assert entity.device_info["identifiers"] == {("openwindows", "test_entry")}


async def test_event_entity_records_reminder(
    hass, freezer, loaded_entry, forecast_response
):
    await hass.config.async_set_time_zone("Europe/Paris")
    start = datetime(2026, 11, 2, 6, 0, tzinfo=PARIS)  # Monday, outside warm season
    freezer.move_to(start)
    entry, coordinator = await loaded_entry()
    await coordinator.mode_manager.async_set_override("force_airing", dt_util.now())
    await hass.async_block_till_done()

    when = datetime(2026, 11, 2, 8, 0, tzinfo=PARIS)
    freezer.move_to(when)
    with patch.object(
        type(hass.services),
        "async_call",
        AsyncMock(return_value=forecast_response()),
    ):
        async_fire_time_changed(hass, when)
        await hass.async_block_till_done()

    state = hass.states.get("event.openwindows_airing_reminder")
    assert state is not None
    assert state.attributes["event_type"] == "morning"
    assert state.attributes["duration_min"] == 4
    assert state.attributes["rooms"] == "Chambre et salon"
    assert state.attributes["outdoor_temp"] == 6.0
