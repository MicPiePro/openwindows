"""Tests for the pure airing slot schedule and duration."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.openwindows.airing import (
    AiringSlot,
    airing_duration_min,
    next_slot,
    weekdays_from_options,
)

TZ = ZoneInfo("Europe/Paris")
ALL_DAYS = frozenset(range(7))
WORK_DAYS = frozenset(range(5))


def _slots(morning_enabled: bool = True, office_enabled: bool = True):
    return [
        AiringSlot("morning", morning_enabled, time(8, 0), ALL_DAYS, "Chambre et salon"),
        AiringSlot("office", office_enabled, time(9, 20), WORK_DAYS, "Bureau"),
    ]


@pytest.mark.parametrize(
    ("temp", "expected"),
    [(15, 5), (10, 5), (8, 5), (7.5, 5), (5, 4), (2, 3), (0, 3), (-5, 3), (None, 4)],
)
def test_duration_values(temp, expected):
    assert airing_duration_min(temp) == expected


def test_duration_never_above_five():
    assert all(3 <= airing_duration_min(t) <= 5 for t in range(-20, 41))


def test_weekdays_from_options():
    assert weekdays_from_options(["mon", "fri", "sun"]) == frozenset({0, 4, 6})


def test_next_slot_same_day():
    now = datetime(2026, 10, 29, 7, 0, tzinfo=TZ)  # Thursday
    when, slot = next_slot(now, _slots())
    assert when == datetime(2026, 10, 29, 8, 0, tzinfo=TZ)
    assert slot.key == "morning"


def test_next_slot_office_after_morning():
    now = datetime(2026, 10, 29, 8, 0, tzinfo=TZ)  # exactly the morning slot
    when, slot = next_slot(now, _slots())
    assert when == datetime(2026, 10, 29, 9, 20, tzinfo=TZ)
    assert slot.key == "office"


def test_next_slot_skips_weekend_office():
    now = datetime(2026, 10, 31, 8, 30, tzinfo=TZ)  # Saturday
    when, slot = next_slot(now, _slots())
    assert when == datetime(2026, 11, 1, 8, 0, tzinfo=TZ)
    assert slot.key == "morning"

    when, slot = next_slot(now, _slots(morning_enabled=False))
    assert when == datetime(2026, 11, 2, 9, 20, tzinfo=TZ)  # Monday
    assert slot.key == "office"


def test_next_slot_none_when_disabled():
    now = datetime(2026, 10, 29, 7, 0, tzinfo=TZ)
    assert next_slot(now, _slots(False, False)) is None


def test_next_slot_none_without_weekdays():
    now = datetime(2026, 10, 29, 7, 0, tzinfo=TZ)
    slots = [AiringSlot("morning", True, time(8, 0), frozenset(), "x")]
    assert next_slot(now, slots) is None


def test_next_slot_across_dst_end():
    now = datetime(2026, 10, 24, 9, 0, tzinfo=TZ)  # Saturday, DST ends Sunday
    when, slot = next_slot(now, _slots())
    assert slot.key == "morning"
    assert when.replace(tzinfo=None) == datetime(2026, 10, 25, 8, 0)
    assert when.utcoffset() == timedelta(hours=1)
