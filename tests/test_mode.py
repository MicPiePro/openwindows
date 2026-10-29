"""Tests for the pure cooling/airing mode rules."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.openwindows.engine import HourForecast
from custom_components.openwindows.mode import (
    MODE_AIRING,
    MODE_COOLING,
    ModeConfig,
    ModeState,
    decide_auto_mode,
    in_warm_season,
    max_within,
    parse_month_day,
)

TZ = ZoneInfo("Europe/Paris")
CFG = ModeConfig()


def _now(month: int, day: int, hour: int = 12) -> datetime:
    return datetime(2026, month, day, hour, tzinfo=TZ)


def test_parse_month_day():
    assert parse_month_day("04-01") == (4, 1)
    assert parse_month_day("02-29") == (2, 29)
    for bad in ("4-1x", "13-01", "02-30"):
        with pytest.raises(ValueError):
            parse_month_day(bad)


def test_in_warm_season_bounds():
    assert in_warm_season(date(2026, 4, 1), CFG) is True
    assert in_warm_season(date(2026, 10, 31), CFG) is True
    assert in_warm_season(date(2026, 3, 31), CFG) is False
    assert in_warm_season(date(2026, 11, 1), CFG) is False
    assert in_warm_season(date(2026, 7, 15), CFG) is True


def test_max_within_window():
    now = _now(7, 1)

    def fc(delta: timedelta, temp: float | None) -> HourForecast:
        return HourForecast(time=now + delta, temp=temp)

    points = [
        fc(timedelta(hours=-1), 35),  # strictly excluded (older than the current hour bucket)
        fc(timedelta(0), 20),
        fc(timedelta(hours=47), 29),
        fc(timedelta(hours=48), 40),  # excluded (upper bound)
    ]
    assert max_within(points, now) == 29
    # the current-hour bucket (started up to 1h ago) is included
    assert max_within([*points, fc(timedelta(minutes=-30), 21)], now) == 29
    assert max_within([fc(timedelta(minutes=-30), 33)], now) == 33
    # points without a temperature are ignored
    assert max_within([fc(timedelta(hours=2), None), fc(timedelta(hours=3), 22)], now) == 22
    assert max_within([fc(timedelta(hours=2), None)], now) is None
    assert max_within([], now) is None


def test_out_of_season_forces_airing_even_in_heat():
    state = ModeState(MODE_COOLING, None)
    assert decide_auto_mode(_now(11, 1), 31.0, state, CFG) == (
        ModeState("airing", None),
        "out_of_season",
    )


def test_first_boot_heat_goes_cooling():
    new, reason = decide_auto_mode(_now(7, 1), 29.0, ModeState(), CFG)
    assert new.mode == MODE_COOLING
    assert reason == "heat_forecast"


def test_first_boot_mild_goes_airing():
    new, reason = decide_auto_mode(_now(7, 1), 24.0, ModeState(), CFG)
    assert new.mode == MODE_AIRING
    assert reason == "no_heat"


def test_airing_stays_between_thresholds():
    new, reason = decide_auto_mode(_now(7, 1), 27.0, ModeState(MODE_AIRING), CFG)
    assert new.mode == MODE_AIRING
    assert reason == "no_heat"


def test_cooling_holds_between_thresholds():
    now = _now(7, 1)
    state = ModeState(MODE_COOLING, now - timedelta(hours=5))
    new, reason = decide_auto_mode(now, 26.0, state, CFG)
    assert new.mode == MODE_COOLING
    assert new.heat_end_since is None
    assert reason == "heat_ongoing"


def test_heat_end_starts_countdown():
    now = _now(7, 1)
    new, reason = decide_auto_mode(now, 22.0, ModeState(MODE_COOLING), CFG)
    assert new.mode == MODE_COOLING
    assert new.heat_end_since == now
    assert reason == "heat_ending"


def test_heat_end_after_two_days_goes_airing():
    now = _now(7, 1)
    state = ModeState(MODE_COOLING, now - timedelta(days=2))
    new, reason = decide_auto_mode(now, 22.0, state, CFG)
    assert new == ModeState(MODE_AIRING, None)
    assert reason == "heat_ended"
    state = ModeState(MODE_COOLING, now - timedelta(hours=47))
    new, reason = decide_auto_mode(now, 22.0, state, CFG)
    assert new.mode == MODE_COOLING
    assert reason == "heat_ending"


def test_cool_night_after_heatwave_stays_cooling():
    # No temperature floor: the night right after a heatwave is still covered.
    now = _now(7, 1, 3)
    state = ModeState(MODE_COOLING, now - timedelta(hours=10))
    new, _ = decide_auto_mode(now, 18.0, state, CFG)
    assert new.mode == MODE_COOLING


def test_no_forecast_keeps_mode():
    now = _now(7, 1)
    since = now - timedelta(hours=3)
    new, reason = decide_auto_mode(now, None, ModeState(MODE_COOLING, since), CFG)
    assert new == ModeState(MODE_COOLING, since)
    assert reason == "no_forecast"
    new, reason = decide_auto_mode(now, None, ModeState(), CFG)
    assert new.mode == MODE_AIRING
    assert reason == "no_forecast"
