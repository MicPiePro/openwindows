"""Pure-pytest tests for the OpenWindows V1 decision engine (no Home Assistant)."""
from datetime import datetime, timedelta

import pytest

from custom_components.openwindows.engine import (
    VERDICT_CLOSE,
    VERDICT_KEEP_CLOSED,
    VERDICT_OPEN,
    VERDICT_OPEN_SOON,
    EngineConfig,
    HourForecast,
    Snapshot,
    ZoneReading,
    ZoneResult,
    decide_verdict,
    find_open_close_window,
    reading_dew_point,
    run_decision_engine,
)
from custom_components.openwindows.psychro import dew_point


# --------------------------------------------------------------------------
# Dataclass defaults / structure
# --------------------------------------------------------------------------
def test_engine_config_defaults():
    cfg = EngineConfig()
    assert cfg.comfort_target == 25.0
    assert cfg.open_margin == 2.0
    assert cfg.close_margin == 0.3
    assert cfg.min_indoor == 23.0
    assert cfg.humidity_gate_enabled is True
    assert cfg.max_outdoor_dewpoint == 18.0


def test_hour_forecast_optional_fields_default_none():
    f = HourForecast(time=datetime(2026, 7, 13, 14, 0, 0), temp=30.0)
    assert f.humidity is None
    assert f.dew_point is None
    assert f.cloud_cover is None
    assert f.solar is None


def test_zone_reading_and_result_fields():
    r = ZoneReading(name="crossvent", temp=29.5, humidity=48.0)
    assert (r.name, r.temp, r.humidity) == ("crossvent", 29.5, 48.0)
    zr = ZoneResult(
        name="crossvent",
        verdict=VERDICT_OPEN,
        indoor_temp=29.5,
        indoor_dew_point=17.0,
        humidity_gate_blocking=False,
    )
    assert zr.verdict == VERDICT_OPEN
    assert zr.humidity_gate_blocking is False


def test_verdict_constant_values():
    assert VERDICT_OPEN == "open"
    assert VERDICT_CLOSE == "close"
    assert VERDICT_KEEP_CLOSED == "keep_closed"
    assert VERDICT_OPEN_SOON == "open_soon"


# --------------------------------------------------------------------------
# reading_dew_point
# --------------------------------------------------------------------------
def test_reading_dew_point_both_present():
    r = ZoneReading(name="bedrooms", temp=30.0, humidity=50.0)
    assert reading_dew_point(r) == pytest.approx(dew_point(30.0, 50.0), abs=1e-9)
    assert reading_dew_point(r) == pytest.approx(18.4409, abs=0.001)


def test_reading_dew_point_missing_temp_is_none():
    assert reading_dew_point(ZoneReading("z", None, 50.0)) is None


def test_reading_dew_point_missing_humidity_is_none():
    assert reading_dew_point(ZoneReading("z", 30.0, None)) is None


# --------------------------------------------------------------------------
# decide_verdict
# --------------------------------------------------------------------------
CFG = EngineConfig()


def test_decide_open_when_outdoor_cool_and_indoor_hot_and_dry():
    # indoor 30C/50% (dew 18.44), outdoor 22C/40% (dew 7.77): clearly open.
    verdict, gate = decide_verdict(
        30.0, dew_point(30.0, 50.0), 22.0, dew_point(22.0, 40.0), False, CFG
    )
    assert verdict == VERDICT_OPEN
    assert gate is False


def test_decide_close_when_outdoor_warmer_than_indoor():
    # outdoor 31 > indoor 29 - 0.3 -> close. Dry outdoor keeps gate False.
    verdict, gate = decide_verdict(
        29.0, dew_point(29.0, 50.0), 31.0, dew_point(31.0, 35.0), False, CFG
    )
    assert verdict == VERDICT_CLOSE
    assert gate is False


def test_humidity_gate_blocks_open_when_outdoor_muggy():
    # Same temps as the open case but outdoor 22C/95% (dew 21.16) exceeds the
    # 18C absolute dew-point cap -> gate blocks; verdict falls to keep_closed.
    verdict, gate = decide_verdict(
        30.0, dew_point(30.0, 50.0), 22.0, dew_point(22.0, 95.0), False, CFG
    )
    assert gate is True
    assert verdict == VERDICT_KEEP_CLOSED


def test_gate_uses_absolute_cap_not_indoor_comparison():
    """Regression for the 'next_open in 5 days' bug.

    The humidity gate must block on an ABSOLUTE outdoor dew-point cap, not on a
    comparison to the (in a heatwave: warm and dry) indoor dew point. Cool humid
    night air whose dew point is below the cap must NOT be gated even when the
    indoor dew point is far lower; genuinely muggy air above the cap is gated.
    """
    cfg = EngineConfig()  # max_outdoor_dewpoint default 18.0
    # Cool night 22C, dew 14.5 (moderately humid); dry indoor 28.7C, dew 13.0.
    # Old logic gated this (14.5 > 13.0 + 1.0); the cap must NOT (14.5 < 18).
    verdict, gate = decide_verdict(28.7, 13.0, 22.0, 14.5, False, cfg)
    assert gate is False
    assert verdict == VERDICT_OPEN
    # Oppressively humid 22C, dew 20.0 (> 18 cap) -> gated -> keep_closed.
    verdict_muggy, gate_muggy = decide_verdict(28.7, 13.0, 22.0, 20.0, False, cfg)
    assert gate_muggy is True
    assert verdict_muggy == VERDICT_KEEP_CLOSED


def test_ac_on_never_opens():
    # Identical to the open case but the AC is running -> must not open.
    verdict, _gate = decide_verdict(
        30.0, dew_point(30.0, 50.0), 22.0, dew_point(22.0, 40.0), True, CFG
    )
    assert verdict != VERDICT_OPEN
    assert verdict == VERDICT_KEEP_CLOSED


def test_decide_keep_closed_when_indoor_comfortable_and_no_close_trigger():
    # indoor 24 (<= comfort_target so no open), outdoor 21 (no close): keep_closed.
    verdict, gate = decide_verdict(
        24.0, dew_point(24.0, 50.0), 21.0, dew_point(21.0, 40.0), False, CFG
    )
    assert verdict == VERDICT_KEEP_CLOSED
    assert gate is False


def test_decide_close_when_indoor_at_or_below_min_indoor():
    # indoor 22.5 <= min_indoor 23 -> close regardless of a cool outdoor.
    verdict, _gate = decide_verdict(
        22.5, dew_point(22.5, 50.0), 15.0, dew_point(15.0, 40.0), False, CFG
    )
    assert verdict == VERDICT_CLOSE


def test_decide_indoor_none_returns_keep_closed_no_gate():
    verdict, gate = decide_verdict(
        None, None, 20.0, dew_point(20.0, 40.0), False, CFG
    )
    assert verdict == VERDICT_KEEP_CLOSED
    assert gate is False


def test_decide_gate_disabled_allows_open_even_if_muggy():
    cfg = EngineConfig(humidity_gate_enabled=False)
    verdict, gate = decide_verdict(
        30.0, dew_point(30.0, 50.0), 22.0, dew_point(22.0, 95.0), False, cfg
    )
    assert gate is False
    assert verdict == VERDICT_OPEN


def test_decide_outdoor_none_keeps_closed():
    verdict, _gate = decide_verdict(
        29.0, dew_point(29.0, 50.0), None, None, False, CFG
    )
    assert verdict == VERDICT_KEEP_CLOSED


# --------------------------------------------------------------------------
# find_open_close_window
# --------------------------------------------------------------------------
NOW = datetime(2026, 7, 13, 14, 0, 0)


def _synthetic_24h(first_temp: float = 33.0, humidity: float = 40.0):
    """Hot afternoon -> cool evening/night -> warming morning, hourly ascending.

    Hours 14:00-18:00 -> 33..29 (hot), 19:00-06:00 -> 20 (cool),
    07:00-13:00 -> warming 20..32. Index 0 is NOW (14:00) at ``first_temp``.
    """
    out = []
    for h in range(24):
        t = NOW + timedelta(hours=h)
        hh = t.hour
        if h == 0:
            temp = first_temp
        elif 14 <= hh < 19:
            temp = 33 - (hh - 14)
        elif hh >= 19 or hh < 7:
            temp = 20.0
        else:
            temp = 20 + (hh - 7) * 2
        out.append(HourForecast(time=t, temp=float(temp), humidity=humidity))
    return out


def test_find_window_returns_evening_open_and_morning_close():
    indoor = ZoneReading("bedrooms", 30.0, 50.0)  # dew 18.44, dry forecast
    next_open, next_close = find_open_close_window(
        NOW, _synthetic_24h(), indoor, CFG
    )
    # First hour where 20C < 30 - 2 and dry -> 19:00 the same evening.
    assert next_open == datetime(2026, 7, 13, 19, 0, 0)
    # First hour AFTER open where outdoor > 30 - 0.3 -> next day 12:00 (30C).
    assert next_close == datetime(2026, 7, 14, 12, 0, 0)


def test_find_window_no_open_when_forecast_never_cool_enough():
    # Flat 31C forecast, indoor 30 -> never opens.
    flat = [
        HourForecast(time=NOW + timedelta(hours=h), temp=31.0, humidity=40.0)
        for h in range(12)
    ]
    indoor = ZoneReading("bedrooms", 30.0, 50.0)
    assert find_open_close_window(NOW, flat, indoor, CFG) == (None, None)


def test_find_window_uses_precomputed_forecast_dew_point_for_gate():
    # Cool but muggy evening (dew set high) must NOT count as an open hour.
    indoor = ZoneReading("bedrooms", 30.0, 50.0)  # indoor dew 18.44
    muggy = [
        HourForecast(
            time=NOW + timedelta(hours=h),
            temp=20.0,
            humidity=None,
            dew_point=25.0,  # 25 > 18 cap -> gate blocks
        )
        for h in range(6)
    ]
    next_open, next_close = find_open_close_window(NOW, muggy, indoor, CFG)
    assert next_open is None
    assert next_close is None


def test_find_window_empty_forecast():
    indoor = ZoneReading("bedrooms", 30.0, 50.0)
    assert find_open_close_window(NOW, [], indoor, CFG) == (None, None)


# --------------------------------------------------------------------------
# run_decision_engine
# --------------------------------------------------------------------------
def _series_24h(first_temp: float, humidity: float = 40.0):
    """Same profile as _synthetic_24h but with a chosen NOW-hour temperature."""
    return _synthetic_24h(first_temp=first_temp, humidity=humidity)


def test_run_engine_ac_off_reference_is_crossvent_and_open_soon():
    # AC off -> reference = crossvent (30C). NOW outdoor 29 gives keep_closed,
    # but a cool evening exists -> promoted to open_soon.
    forecasts = _series_24h(29.0)
    snap = run_decision_engine(
        NOW,
        forecasts,
        crossvent=ZoneReading("crossvent", 30.0, 50.0),
        bedrooms=ZoneReading("bedrooms", 28.0, 50.0),
        bureau=ZoneReading("bureau", 27.0, 55.0),
        ac_on=False,
        door_open=False,
        cfg=CFG,
    )
    assert isinstance(snap, Snapshot)
    assert snap.reference_zone == "crossvent"
    assert snap.indoor_ref_temp == 30.0
    assert snap.outdoor_temp == 29.0
    assert snap.ac_on is False
    assert snap.verdict == VERDICT_OPEN_SOON
    assert snap.reason == "open_soon"
    assert snap.next_open == datetime(2026, 7, 13, 19, 0, 0)
    assert snap.next_close == datetime(2026, 7, 14, 12, 0, 0)
    # degrees_saved = peak(32) - ref(30) = 2.0
    assert snap.degrees_saved == pytest.approx(2.0, abs=1e-9)


def test_run_engine_ac_on_switches_reference_to_bedrooms():
    # AC on and salon/cuisine (crossvent) reads AC-depressed 24C -> reference
    # must switch to the warm bedrooms (30C).
    forecasts = _series_24h(22.0)
    snap = run_decision_engine(
        NOW,
        forecasts,
        crossvent=ZoneReading("crossvent", 24.0, 55.0),
        bedrooms=ZoneReading("bedrooms", 30.0, 50.0),
        bureau=ZoneReading("bureau", 27.0, 55.0),
        ac_on=True,
        door_open=False,
        cfg=CFG,
    )
    assert snap.reference_zone == "bedrooms"
    assert snap.indoor_ref_temp == 30.0
    assert snap.ac_on is True
    # AC on -> never OPEN and never promoted to OPEN_SOON.
    assert snap.verdict == VERDICT_KEEP_CLOSED
    assert snap.outdoor_temp == 22.0


def test_run_engine_populates_zone_results():
    forecasts = _series_24h(29.0)
    snap = run_decision_engine(
        NOW,
        forecasts,
        crossvent=ZoneReading("crossvent", 30.0, 50.0),
        bedrooms=ZoneReading("bedrooms", 28.0, 50.0),
        bureau=ZoneReading("bureau", 27.0, 55.0),
        ac_on=False,
        door_open=False,
        cfg=CFG,
    )
    assert set(snap.zones) == {"crossvent", "bureau"}
    # crossvent 30 vs outdoor 29: no open (29 !< 28), no close (29 !> 29.7).
    assert snap.zones["crossvent"].verdict == VERDICT_KEEP_CLOSED
    assert snap.zones["crossvent"].indoor_temp == 30.0
    # bureau 27 vs outdoor 29: 29 > 27 - 0.3 -> close.
    assert snap.zones["bureau"].verdict == VERDICT_CLOSE
    assert snap.zones["bureau"].indoor_temp == 27.0


def test_run_engine_forecast_series_shape():
    forecasts = _series_24h(29.0)
    snap = run_decision_engine(
        NOW,
        forecasts,
        crossvent=ZoneReading("crossvent", 30.0, 50.0),
        bedrooms=ZoneReading("bedrooms", 28.0, 50.0),
        bureau=ZoneReading("bureau", 27.0, 55.0),
        ac_on=False,
        door_open=False,
        cfg=CFG,
    )
    assert len(snap.forecast_series) == 24
    first = snap.forecast_series[0]
    assert first["time_iso"] == "2026-07-13T14:00:00"
    assert first["outdoor"] == 29.0
    # V1: indoor_pred simply holds the reference temp (no RC model).
    assert first["indoor_pred"] == 30.0
    assert first["comfort"] == 25.0


def test_run_engine_current_verdict_close_when_outdoor_hot_now():
    # NOW outdoor 33 > ref 30 - 0.3 -> global verdict close.
    forecasts = _series_24h(33.0)
    snap = run_decision_engine(
        NOW,
        forecasts,
        crossvent=ZoneReading("crossvent", 30.0, 50.0),
        bedrooms=ZoneReading("bedrooms", 28.0, 50.0),
        bureau=ZoneReading("bureau", 27.0, 55.0),
        ac_on=False,
        door_open=False,
        cfg=CFG,
    )
    assert snap.verdict == VERDICT_CLOSE
    assert snap.reason == "outdoor_warm"
