"""Tests for the AiringScheduler (morning/office airing reminders)."""
from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.openwindows.airing_scheduler import (
    AiringScheduler,
    airing_slots_from_options,
)
from custom_components.openwindows.const import (
    CONF_MORNING_ENABLED,
    CONF_OFFICE_DAYS,
    CONF_OFFICE_TIME,
    DOMAIN,
)

PARIS = ZoneInfo("Europe/Paris")


class FakeModeManager:
    """Minimal ModeManager stand-in: mode, last_outdoor_temp, listeners."""

    def __init__(self, mode: str = "airing", temp: float | None = 6.0) -> None:
        self.mode = mode
        self.last_outdoor_temp = temp
        self._listeners = []

    def async_add_listener(self, cb):
        self._listeners.append(cb)
        return lambda: self._listeners.remove(cb)

    def notify(self) -> None:
        for cb in list(self._listeners):
            cb()


@pytest.fixture
async def paris(hass):
    await hass.config.async_set_time_zone("Europe/Paris")


def _local(*args) -> datetime:
    return datetime(*args, tzinfo=PARIS)


def _scheduler(hass, manager, options=None) -> AiringScheduler:
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=options or {})
    entry.add_to_hass(hass)
    return AiringScheduler(hass, entry, manager)


async def _fire(hass, freezer, when: datetime) -> None:
    freezer.move_to(when)
    async_fire_time_changed(hass, when)
    await hass.async_block_till_done()


def test_airing_slots_from_options_defaults_and_parsing():
    morning, office = airing_slots_from_options({})
    assert (morning.key, morning.enabled, morning.at) == ("morning", True, time(8, 0))
    assert morning.weekdays == frozenset(range(7))
    assert morning.rooms == "Chambre et salon"
    assert (office.key, office.enabled, office.at) == ("office", True, time(9, 20))
    assert office.weekdays == frozenset(range(5))
    assert office.rooms == "Bureau"

    morning, office = airing_slots_from_options(
        {
            CONF_MORNING_ENABLED: False,
            CONF_OFFICE_TIME: "10:05",
            CONF_OFFICE_DAYS: ["sat"],
        }
    )
    assert morning.enabled is False
    assert office.at == time(10, 5)
    assert office.weekdays == frozenset({5})


async def test_fires_morning_reminder_in_airing(hass, paris, freezer):
    freezer.move_to(_local(2026, 11, 2, 6, 0))  # Monday
    scheduler = _scheduler(hass, FakeModeManager("airing", 6))
    received = []
    scheduler.async_add_reminder_listener(lambda key, data: received.append((key, data)))
    scheduler.async_start()

    await _fire(hass, freezer, _local(2026, 11, 2, 8, 0))

    assert received == [
        (
            "morning",
            {"rooms": "Chambre et salon", "duration_min": 4, "outdoor_temp": 6},
        )
    ]
    scheduler.async_stop()


async def test_no_reminder_in_cooling(hass, paris, freezer):
    freezer.move_to(_local(2026, 7, 6, 6, 0))
    manager = FakeModeManager("cooling", 20)
    scheduler = _scheduler(hass, manager)
    received = []
    scheduler.async_add_reminder_listener(lambda key, data: received.append(key))
    scheduler.async_start()

    await _fire(hass, freezer, _local(2026, 7, 6, 8, 0))
    assert received == []

    # The timer was rescheduled: switching to airing makes the next slot fire.
    manager.mode = "airing"
    await _fire(hass, freezer, _local(2026, 7, 6, 9, 20))
    assert received == ["office"]
    scheduler.async_stop()


async def test_office_not_on_saturday(hass, paris, freezer):
    freezer.move_to(_local(2026, 10, 31, 8, 30))  # Saturday, after the morning slot
    scheduler = _scheduler(hass, FakeModeManager())
    received = []
    scheduler.async_add_reminder_listener(lambda key, data: received.append(key))
    scheduler.async_start()

    # Next occurrence is Sunday's morning; Saturday 09:20 office is skipped.
    assert scheduler.next_airing == _local(2026, 11, 1, 8, 0)
    await _fire(hass, freezer, _local(2026, 10, 31, 9, 20))
    assert received == []
    await _fire(hass, freezer, _local(2026, 11, 1, 8, 0))
    assert received == ["morning"]
    # Sunday has no office slot either; the next one is Monday morning.
    assert scheduler.next_airing == _local(2026, 11, 2, 8, 0)
    scheduler.async_stop()


async def test_reminder_fires_with_unknown_temp(hass, paris, freezer):
    freezer.move_to(_local(2026, 11, 2, 6, 0))
    scheduler = _scheduler(hass, FakeModeManager("airing", None))
    received = []
    scheduler.async_add_reminder_listener(lambda key, data: received.append(data))
    scheduler.async_start()

    await _fire(hass, freezer, _local(2026, 11, 2, 8, 0))

    assert received[0]["duration_min"] == 4
    assert received[0]["outdoor_temp"] is None
    scheduler.async_stop()


async def test_does_not_fire_on_start_and_reschedules_from_fired_slot(
    hass, paris, freezer
):
    freezer.move_to(_local(2026, 11, 2, 8, 30))  # after morning, before office
    scheduler = _scheduler(hass, FakeModeManager())
    received = []
    scheduler.async_add_reminder_listener(lambda key, data: received.append(key))
    scheduler.async_start()
    await hass.async_block_till_done()
    assert received == []
    assert scheduler.next_slot_key == "office"

    await _fire(hass, freezer, _local(2026, 11, 2, 9, 20))
    assert received == ["office"]
    assert scheduler.next_airing == _local(2026, 11, 3, 8, 0)
    assert scheduler.next_slot_key == "morning"
    scheduler.async_stop()


async def test_next_airing_none_in_cooling_and_set_in_airing(hass, paris, freezer):
    freezer.move_to(_local(2026, 11, 2, 6, 0))
    manager = FakeModeManager("cooling")
    scheduler = _scheduler(hass, manager)
    calls = []
    scheduler.async_add_listener(lambda: calls.append(1))
    scheduler.async_start()
    assert scheduler.next_airing is None
    assert scheduler.next_slot_key is None
    calls.clear()

    manager.mode = "airing"
    manager.notify()  # the scheduler re-notifies its own listeners
    assert calls == [1]
    assert scheduler.next_airing == _local(2026, 11, 2, 8, 0)
    assert scheduler.next_slot_key == "morning"
    scheduler.async_stop()


async def test_listener_unsubscribe(hass, paris, freezer):
    freezer.move_to(_local(2026, 11, 2, 6, 0))
    manager = FakeModeManager()
    scheduler = _scheduler(hass, manager)
    calls = []
    unsub = scheduler.async_add_listener(lambda: calls.append(1))
    scheduler.async_start()
    calls.clear()
    unsub()
    manager.notify()
    assert calls == []
    scheduler.async_stop()


async def test_no_enabled_slot_means_no_timer(hass, paris, freezer):
    freezer.move_to(_local(2026, 11, 2, 6, 0))
    scheduler = _scheduler(
        hass,
        FakeModeManager(),
        {"morning_enabled": False, "office_enabled": False},
    )
    scheduler.async_start()
    assert scheduler.next_airing is None
    assert scheduler.next_slot_key is None
    scheduler.async_stop()


async def test_stop_cancels_timer(hass, paris, freezer):
    freezer.move_to(_local(2026, 11, 2, 6, 0))
    manager = FakeModeManager()
    scheduler = _scheduler(hass, manager)
    received = []
    scheduler.async_add_reminder_listener(lambda key, data: received.append(key))
    scheduler.async_start()
    scheduler.async_stop()

    await _fire(hass, freezer, _local(2026, 11, 2, 8, 0))
    assert received == []
    assert manager._listeners == []  # mode-manager subscription released


async def test_dst_slot_is_local_time(hass, paris, freezer):
    # Spring forward 2027-03-28 (02:00 -> 03:00): 08:00 local is UTC+2 afterwards.
    freezer.move_to(_local(2027, 3, 27, 9, 0))
    scheduler = _scheduler(hass, FakeModeManager())
    scheduler.async_start()
    nxt = scheduler.next_airing
    assert nxt == _local(2027, 3, 28, 8, 0)
    assert dt_util.as_utc(nxt).hour == 6
    scheduler.async_stop()
