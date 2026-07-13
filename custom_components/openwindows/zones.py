"""Pure zone aggregation for OpenWindows.

No Home Assistant imports here: this module is unit-tested with plain pytest.
"""
from __future__ import annotations

from .engine import ZoneReading


def _mean(values: list[float | None]) -> float | None:
    """Return the arithmetic mean of the non-None values, or None if empty."""
    present = [v for v in values if v is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _max(values: list[float | None]) -> float | None:
    """Return the maximum of the non-None values, or None if empty."""
    present = [v for v in values if v is not None]
    if not present:
        return None
    return max(present)


def aggregate_zone(
    name: str,
    temps: list[float | None],
    hums: list[float | None],
) -> ZoneReading:
    """Aggregate a zone's sensor lists into a single ZoneReading.

    Temperature is the MAX of the non-None values (the hottest room drives the
    decision to open/close). Humidity stays the mean of the non-None values
    and is informational only. An empty (or all-None) list yields None for
    that field.
    """
    return ZoneReading(name=name, temp=_max(temps), humidity=_mean(hums))
