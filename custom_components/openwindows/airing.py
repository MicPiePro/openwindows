"""Pure airing rules for OpenWindows (no Home Assistant).

In ``airing`` mode the integration announces short timed airings at
configurable daily slots (e.g. morning, office). This module holds the slot
schedule and the airing duration.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

# Same order as const.WEEKDAY_OPTIONS (const.py pulls in Home Assistant, so this
# module deliberately does not import it); index == date.weekday().
_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


@dataclass
class AiringSlot:
    """One configurable airing slot. Weekdays use ``date.weekday()`` (Mon = 0)."""

    key: str
    enabled: bool
    at: time
    weekdays: frozenset[int]
    rooms: str


def weekdays_from_options(days: list[str]) -> frozenset[int]:
    """Convert option values (``"mon"`` ... ``"sun"``) to weekday numbers."""
    return frozenset(_WEEKDAYS.index(d) for d in days)


def next_slot(
    now_local: datetime, slots: list[AiringSlot]
) -> tuple[datetime, AiringSlot] | None:
    """Return the earliest enabled slot occurrence strictly after ``now_local``.

    Searches today plus the next 7 days. Candidates are built in the timezone of
    ``now_local``. Returns None if no slot is enabled or none has weekdays.
    """
    today: date = now_local.date()
    best: tuple[datetime, AiringSlot] | None = None
    for offset in range(8):
        day = today + timedelta(days=offset)
        for slot in slots:
            if not slot.enabled or day.weekday() not in slot.weekdays:
                continue
            candidate = datetime.combine(day, slot.at, tzinfo=now_local.tzinfo)
            if candidate <= now_local:
                continue
            if best is None or candidate < best[0]:
                best = (candidate, slot)
        if best is not None:
            # Days are scanned in order, so a later day cannot beat this one.
            break
    return best


def airing_duration_min(outdoor_temp: float | None) -> int:
    """Airing length in minutes: 3 (cold) to 5 (mild); 4 when unknown."""
    if outdoor_temp is None:
        return 4
    clamped = min(max(outdoor_temp, 0.0), 10.0)
    return math.floor(3 + clamped / 10 * 2 + 0.5)
