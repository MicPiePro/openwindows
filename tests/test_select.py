"""Tests for the mode override select entity."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

PARIS = ZoneInfo("Europe/Paris")
ENTITY = "select.openwindows_mode_override"


async def test_select_force_airing_updates_mode_and_refreshes(
    hass, freezer, loaded_entry
):
    await hass.config.async_set_time_zone("Europe/Paris")
    freezer.move_to(datetime(2026, 7, 15, 12, 0, tzinfo=PARIS))  # warm season
    _, coordinator = await loaded_entry()

    state = hass.states.get(ENTITY)
    assert state.state == "auto"
    assert state.attributes["options"] == ["auto", "force_cooling", "force_airing"]

    with patch.object(
        coordinator, "async_request_refresh", AsyncMock()
    ) as refresh:
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": ENTITY, "option": "force_airing"},
            blocking=True,
        )
    refresh.assert_awaited_once()

    assert coordinator.mode_manager.mode == "airing"
    assert coordinator.mode_manager.source == "override"
    assert hass.states.get(ENTITY).state == "force_airing"
    assert hass.states.get("sensor.openwindows_mode").state == "airing"


async def test_select_reflects_expiry_back_to_auto(hass, freezer, loaded_entry):
    await hass.config.async_set_time_zone("Europe/Paris")
    freezer.move_to(datetime(2026, 11, 2, 6, 0, tzinfo=PARIS))
    _, coordinator = await loaded_entry()
    manager = coordinator.mode_manager

    await manager.async_set_override("force_cooling", dt_util.now())
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY).state == "force_cooling"

    later = dt_util.now() + timedelta(days=2)
    await manager.async_update(later, None)
    await hass.async_block_till_done()

    assert hass.states.get(ENTITY).state == "auto"
    assert manager.override_option == "auto"
