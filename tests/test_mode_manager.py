"""Tests for the ModeManager (mode state, override, persistence)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openwindows.const import (
    CONF_HEAT_END_DAYS,
    CONF_HEAT_THRESHOLD,
    CONF_WARM_SEASON_END,
    CONF_WARM_SEASON_START,
    DOMAIN,
)
from custom_components.openwindows.engine import HourForecast
from custom_components.openwindows.mode import ModeConfig
from custom_components.openwindows.mode_manager import (
    ModeManager,
    mode_config_from_options,
)

UTC = UTC


def _entry(hass, options=None):
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=options or {})
    entry.add_to_hass(hass)
    return entry


def _fc(now, *temps):
    """Hourly forecast points starting at ``now``."""
    return [
        HourForecast(time=now + timedelta(hours=i), temp=t)
        for i, t in enumerate(temps)
    ]


JUL1 = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
NOV3 = datetime(2026, 11, 3, 10, 0, tzinfo=UTC)


def test_mode_config_from_options_defaults_and_coercion():
    assert mode_config_from_options({}) == ModeConfig()
    cfg = mode_config_from_options(
        {
            CONF_WARM_SEASON_START: "05-15",
            CONF_WARM_SEASON_END: "09-30",
            CONF_HEAT_THRESHOLD: 30,
            CONF_HEAT_END_DAYS: 2.0,
        }
    )
    assert cfg.warm_season_start == (5, 15)
    assert cfg.warm_season_end == (9, 30)
    assert cfg.heat_threshold == 30.0 and isinstance(cfg.heat_threshold, float)
    assert cfg.heat_end_days == 2 and isinstance(cfg.heat_end_days, int)


async def test_default_mode_is_airing_before_update(hass):
    mgr = ModeManager(hass, _entry(hass))
    assert mgr.mode == "airing"
    assert mgr.source == "auto"
    assert mgr.override_option == "auto"
    assert mgr.override_until is None
    assert mgr.override_days == 1


async def test_update_heat_goes_cooling(hass):
    mgr = ModeManager(hass, _entry(hass))
    await mgr.async_update(JUL1, _fc(JUL1, 30.0))
    assert mgr.mode == "cooling"
    assert mgr.reason == "heat_forecast"
    assert mgr.max_48h == 30
    assert mgr.source == "auto"
    assert mgr.in_warm_season is True
    assert mgr.last_outdoor_temp == 30.0


async def test_forced_override_wins_and_expires(hass):
    mgr = ModeManager(hass, _entry(hass))
    await mgr.async_set_override("force_cooling", NOV3)
    assert mgr.mode == "cooling"
    assert mgr.source == "override"
    assert mgr.reason == "override"
    assert mgr.override_until == NOV3 + timedelta(days=1)

    later = datetime(2026, 11, 4, 10, 1, tzinfo=UTC)
    await mgr.async_update(later, _fc(later, 10.0))
    assert mgr.mode == "airing"
    assert mgr.source == "auto"
    assert mgr.override_option == "auto"
    assert mgr.override_until is None


async def test_override_days_change_does_not_move_running_expiry(hass):
    mgr = ModeManager(hass, _entry(hass))
    await mgr.async_set_override("force_airing", NOV3)
    until = mgr.override_until
    await mgr.async_set_override_days(5)
    assert mgr.override_days == 5
    assert mgr.override_until == until
    await mgr.async_set_override("force_cooling", NOV3)
    assert mgr.override_until == NOV3 + timedelta(days=5)


async def test_auto_clears_override(hass):
    mgr = ModeManager(hass, _entry(hass))
    await mgr.async_set_override("force_cooling", NOV3)
    await mgr.async_set_override("auto", NOV3)
    assert mgr.override_option == "auto"
    assert mgr.override_until is None
    assert mgr.source == "auto"
    assert mgr.mode == "airing"


async def test_listener_called_on_update_and_override(hass):
    mgr = ModeManager(hass, _entry(hass))
    calls = []
    unsub = mgr.async_add_listener(lambda: calls.append(1))
    await mgr.async_update(JUL1, _fc(JUL1, 20.0))
    assert len(calls) == 1
    await mgr.async_set_override("force_cooling", JUL1)
    assert len(calls) == 2
    unsub()
    await mgr.async_set_override("auto", JUL1)
    assert len(calls) == 2


async def test_state_survives_reload(hass):
    entry = _entry(hass)
    now = dt_util.now()
    # Warm-season dates are local; use a July date regardless of today's date.
    warm = now.replace(month=7, day=1, hour=12)
    a = ModeManager(hass, entry)
    await a.async_update(warm, _fc(warm, 30.0))
    assert a.mode == "cooling"
    # Cool-down: heat_ending starts the countdown.
    t1 = warm + timedelta(days=3)
    await a.async_update(t1, _fc(t1, 20.0))
    assert a.reason == "heat_ending"
    since = a._state.heat_end_since
    assert since == t1
    await a.async_set_override("force_airing", now)
    until = a.override_until

    b = ModeManager(hass, entry)
    await b.async_load()
    assert b.override_until == until
    assert b.override_option == "force_airing"
    assert b.mode == a.mode == "airing"
    assert b._state.heat_end_since == since

    # Countdown continues: a later update keeps the original start.
    t2 = t1 + timedelta(hours=6)
    await b.async_update(t2, _fc(t2, 20.0))
    assert b.reason == "override"  # forced airing still masks the auto reason
    assert b._reason == "heat_ending"
    assert b._state.heat_end_since == since
    assert b._state.mode == "cooling"


async def test_expired_override_cleared_on_load(hass):
    entry = _entry(hass)
    a = ModeManager(hass, entry)
    past = datetime(2020, 1, 1, 10, 0, tzinfo=UTC)
    await a.async_set_override("force_cooling", past)

    b = ModeManager(hass, entry)
    await b.async_load()
    assert b.override_option == "auto"
    assert b.override_until is None
    assert b.source == "auto"
    assert b.mode == "airing"


async def test_update_without_forecast_keeps_mode(hass):
    mgr = ModeManager(hass, _entry(hass))
    await mgr.async_update(JUL1, _fc(JUL1, 30.0))
    assert mgr.mode == "cooling"
    later = JUL1 + timedelta(hours=1)
    await mgr.async_update(later, None)
    assert mgr.mode == "cooling"
    assert mgr.reason == "no_forecast"
    assert mgr.max_48h is None
    assert mgr.last_outdoor_temp is None
