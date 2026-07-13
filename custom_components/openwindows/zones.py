"""Pure zone aggregation and reference selection for OpenWindows.

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


def mean_reading(
    name: str,
    temps: list[float | None],
    hums: list[float | None],
) -> ZoneReading:
    """Aggregate a zone's sensor lists into a single ZoneReading.

    Temperature and humidity are each the mean of their non-None values;
    an empty (or all-None) list yields None for that field.
    """
    return ZoneReading(name=name, temp=_mean(temps), humidity=_mean(hums))


def select_reference(
    crossvent: ZoneReading,
    bedrooms: ZoneReading,
    ac_on: bool,
) -> tuple[ZoneReading, str]:
    """Choose the indoor reference zone.

    When the portable AC is running, the crossvent (salon/cuisine) sensors are
    AC-depressed, so prefer the bedroom sensors — but only if the bedrooms
    actually report a temperature. Otherwise fall back to crossvent.
    """
    if ac_on and bedrooms.temp is not None:
        return bedrooms, "bedrooms"
    return crossvent, "crossvent"
