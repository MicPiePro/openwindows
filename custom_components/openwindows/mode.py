"""Pure cooling/airing mode rules for OpenWindows (no Home Assistant).

The integration runs in one of two modes:

* ``cooling``: summer behaviour, the open/close verdicts of the engine.
* ``airing``: short timed airings (morning, office) instead of continuous
  advice; the engine verdicts are reported as ``inactive``.

`decide_auto_mode` picks the mode from the 48 h forecast peak, with a
hysteresis so a heatwave is not abandoned at the first cool reading.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .engine import HourForecast

# Values kept in sync with const.MODE_* / const.VERDICT_INACTIVE (const.py pulls
# in Home Assistant, so this module deliberately does not import it).
MODE_COOLING = "cooling"
MODE_AIRING = "airing"
VERDICT_INACTIVE = "inactive"

_MONTH_DAY = re.compile(r"^(\d{2})-(\d{2})$")


@dataclass
class ModeConfig:
    """Tunable thresholds (mirrors the OPTIONS keys in const.py).

    Season bounds are ``(month, day)`` tuples, both inclusive.
    """

    warm_season_start: tuple[int, int] = (4, 1)
    warm_season_end: tuple[int, int] = (10, 31)
    heat_threshold: float = 28.0
    heat_end_threshold: float = 25.0
    heat_end_days: int = 2


@dataclass
class ModeState:
    """Automatic-mode state carried between decisions."""

    mode: str | None = None
    heat_end_since: datetime | None = None


def parse_month_day(value: str) -> tuple[int, int]:
    """Parse ``"MM-DD"`` into ``(month, day)``; raise ValueError if invalid.

    The date is validated against leap year 2024 so ``02-29`` is accepted.
    """
    match = _MONTH_DAY.match(value.strip())
    if match is None:
        raise ValueError(f"Invalid month-day {value!r}, expected MM-DD")
    month, day = int(match.group(1)), int(match.group(2))
    date(2024, month, day)  # raises ValueError on an impossible date
    return month, day


def in_warm_season(today: date, cfg: ModeConfig) -> bool:
    """True if ``today`` is within the warm season (inclusive bounds)."""
    return cfg.warm_season_start <= (today.month, today.day) <= cfg.warm_season_end


def max_within(
    forecasts: list[HourForecast], now: datetime, hours: int = 48
) -> float | None:
    """Highest forecast temp over the next ``hours`` hours, or None.

    Keeps points with ``now - 1h < time < now + hours``: hourly forecasts start
    with the current-hour bucket, which began up to one hour ago. Points
    without a temperature are ignored.
    """
    start = now - timedelta(hours=1)
    end = now + timedelta(hours=hours)
    temps = [
        f.temp for f in forecasts if f.temp is not None and start < f.time < end
    ]
    return max(temps) if temps else None


def decide_auto_mode(
    now: datetime,
    max_48h: float | None,
    state: ModeState,
    cfg: ModeConfig,
) -> tuple[ModeState, str]:
    """Return the new automatic mode state and a machine ``reason`` slug."""
    if not in_warm_season(now.date(), cfg):
        return ModeState(MODE_AIRING, None), "out_of_season"
    if max_48h is None:
        return ModeState(state.mode or MODE_AIRING, state.heat_end_since), "no_forecast"
    if max_48h >= cfg.heat_threshold:
        return ModeState(MODE_COOLING, None), "heat_forecast"
    if state.mode != MODE_COOLING:  # includes first boot (None)
        return ModeState(MODE_AIRING, None), "no_heat"
    if max_48h >= cfg.heat_end_threshold:
        return ModeState(MODE_COOLING, None), "heat_ongoing"
    since = state.heat_end_since or now
    if now - since >= timedelta(days=cfg.heat_end_days):
        return ModeState(MODE_AIRING, None), "heat_ended"
    return ModeState(MODE_COOLING, since), "heat_ending"
