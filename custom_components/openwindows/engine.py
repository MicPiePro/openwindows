"""Pure V1 decision engine for OpenWindows (no numpy, no Home Assistant).

Simple crossover + hysteresis + dew-point gate. The 2-node RC model and the
matplotlib PNG live in a separate V2 plan and are intentionally absent here.

The indoor reference is simply the cross-vent zone reading (the hottest room
among its sensors, see `zones.aggregate_zone`); there is no separate AC-aware
reference selection.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .psychro import dew_point

# Verdict values (kept in sync with const.VERDICT_* by value; engine stays pure
# so it deliberately does not import const.py, which pulls in Home Assistant).
VERDICT_OPEN = "open"
VERDICT_CLOSE = "close"
VERDICT_KEEP_CLOSED = "keep_closed"
VERDICT_OPEN_SOON = "open_soon"


@dataclass
class HourForecast:
    """One hourly forecast point (any weather source, normalised)."""

    time: datetime
    temp: float
    humidity: float | None = None
    dew_point: float | None = None
    cloud_cover: float | None = None
    solar: float | None = None


@dataclass
class ZoneReading:
    """Aggregated indoor reading for a zone (max temp, mean humidity)."""

    name: str
    temp: float | None
    humidity: float | None


@dataclass
class EngineConfig:
    """Tunable thresholds (mirrors the OPTIONS keys in const.py)."""

    comfort_target: float = 25.0
    open_margin: float = 2.0
    close_margin: float = 0.3
    min_indoor: float = 23.0
    humidity_gate_enabled: bool = True
    max_outdoor_dewpoint: float = 18.0


@dataclass
class ZoneResult:
    """Per-zone verdict and the numbers behind it."""

    name: str
    verdict: str
    indoor_temp: float | None
    indoor_dew_point: float | None
    humidity_gate_blocking: bool


@dataclass
class Snapshot:
    """Full engine output consumed by the coordinator / entities."""

    verdict: str
    reason: str
    next_open: datetime | None
    next_close: datetime | None
    outdoor_temp: float | None
    outdoor_dew_point: float | None
    indoor_ref_temp: float | None
    humidity_gate_blocking: bool
    zones: dict[str, ZoneResult]
    forecast_series: list[dict]
    degrees_saved: float | None


def reading_dew_point(r: ZoneReading) -> float | None:
    """Dew point of a zone reading, or None when temp or humidity is missing."""
    if r.temp is None or r.humidity is None:
        return None
    return dew_point(r.temp, r.humidity)


def decide_verdict(
    indoor_temp: float | None,
    indoor_dew_point: float | None,
    outdoor_temp: float | None,
    outdoor_dew_point: float | None,
    cfg: EngineConfig,
) -> tuple[str, bool]:
    """Return (verdict, humidity_gate_blocking) for one moment in time.

    Gate blocks when the outdoor air is objectively muggy (absolute cap):
        gate = humidity_gate_enabled and outdoor_dew_point known and
               outdoor_dew_point > max_outdoor_dewpoint.
    indoor_dew_point is kept in the signature for compatibility but the gate no
    longer compares against it: a warm, dry heatwave indoor has an artificially
    low dew point, which wrongly blocked beneficial cool-but-humid night air.

    Rules (in order):
      - indoor_temp unknown -> (keep_closed, False)
      - open  if outdoor < indoor - open_margin and indoor > comfort_target
              and gate not blocking
      - close if outdoor > indoor - close_margin or indoor <= min_indoor
      - otherwise keep_closed
    """
    gate_blocking = (
        cfg.humidity_gate_enabled
        and outdoor_dew_point is not None
        and outdoor_dew_point > cfg.max_outdoor_dewpoint
    )

    if indoor_temp is None:
        return (VERDICT_KEEP_CLOSED, False)

    if outdoor_temp is None:
        if indoor_temp <= cfg.min_indoor:
            return (VERDICT_CLOSE, gate_blocking)
        return (VERDICT_KEEP_CLOSED, gate_blocking)

    if (
        outdoor_temp < indoor_temp - cfg.open_margin
        and indoor_temp > cfg.comfort_target
        and not gate_blocking
    ):
        return (VERDICT_OPEN, gate_blocking)

    if outdoor_temp > indoor_temp - cfg.close_margin or indoor_temp <= cfg.min_indoor:
        return (VERDICT_CLOSE, gate_blocking)

    return (VERDICT_KEEP_CLOSED, gate_blocking)


def _forecast_dew_point(f: HourForecast) -> float | None:
    """Dew point for a forecast hour: use the precomputed value, else derive it."""
    if f.dew_point is not None:
        return f.dew_point
    if f.humidity is not None:
        return dew_point(f.temp, f.humidity)
    return None


def find_open_close_window(
    now: datetime,
    forecasts: list[HourForecast],
    indoor_ref: ZoneReading,
    cfg: EngineConfig,
) -> tuple[datetime | None, datetime | None]:
    """Scan an ascending hourly forecast for the next open then close times.

    next_open  = first hour whose OPEN condition holds.
    next_close = first hour AFTER next_open whose CLOSE condition holds
                 (outdoor > indoor - close_margin or indoor <= min_indoor).
    Returns (None, None) parts that are never reached.
    """
    indoor_dp = reading_dew_point(indoor_ref)
    indoor_temp = indoor_ref.temp
    next_open: datetime | None = None
    next_close: datetime | None = None

    for f in forecasts:
        outdoor_dp = _forecast_dew_point(f)
        if next_open is None:
            verdict, _gate = decide_verdict(
                indoor_temp, indoor_dp, f.temp, outdoor_dp, cfg
            )
            if verdict == VERDICT_OPEN:
                next_open = f.time
            continue
        # After an open hour: look for the first close-condition hour.
        if indoor_temp is not None and (
            f.temp > indoor_temp - cfg.close_margin or indoor_temp <= cfg.min_indoor
        ):
            next_close = f.time
            break

    return (next_open, next_close)


def _reason_for(
    verdict: str, gate_blocking: bool, indoor_temp: float | None, cfg: EngineConfig
) -> str:
    """Stable machine-readable reason slug for the global verdict."""
    if verdict == VERDICT_OPEN:
        return "open_now"
    if verdict == VERDICT_OPEN_SOON:
        return "open_soon"
    if verdict == VERDICT_CLOSE:
        if indoor_temp is not None and indoor_temp <= cfg.min_indoor:
            return "indoor_cool"
        return "outdoor_warm"
    # keep_closed
    return "gate_humid" if gate_blocking else "no_benefit"


def run_decision_engine(
    now: datetime,
    forecasts: list[HourForecast],
    crossvent: ZoneReading,
    bureau: ZoneReading,
    door_open: bool,
    cfg: EngineConfig,
) -> Snapshot:
    """Compute the full Snapshot for the current moment plus the forecast window.

    - The indoor reference IS the cross-vent zone reading (its temperature is
      already the hottest room among its sensors, see zones.aggregate_zone).
    - Global verdict comes from the reference reading vs forecasts[0]. When the
      current verdict is keep_closed and a future open hour exists, the
      verdict is promoted to open_soon.
    - Per-zone results are produced for the cross-vent core and the bureau.
    """
    reference = crossvent
    ref_dp = reading_dew_point(reference)

    current = forecasts[0] if forecasts else None
    outdoor_temp = current.temp if current is not None else None
    outdoor_dp = _forecast_dew_point(current) if current is not None else None

    base_verdict, gate_blocking = decide_verdict(
        reference.temp, ref_dp, outdoor_temp, outdoor_dp, cfg
    )
    next_open, next_close = find_open_close_window(now, forecasts, reference, cfg)

    verdict = base_verdict
    if base_verdict == VERDICT_KEEP_CLOSED and next_open is not None:
        verdict = VERDICT_OPEN_SOON

    # Per-zone results.
    cv_dp = reading_dew_point(crossvent)
    cv_verdict, cv_gate = decide_verdict(
        crossvent.temp, cv_dp, outdoor_temp, outdoor_dp, cfg
    )
    bu_dp = reading_dew_point(bureau)
    bu_verdict, bu_gate = decide_verdict(
        bureau.temp, bu_dp, outdoor_temp, outdoor_dp, cfg
    )
    zones: dict[str, ZoneResult] = {
        "crossvent": ZoneResult(
            "crossvent", cv_verdict, crossvent.temp, cv_dp, cv_gate
        ),
        "bureau": ZoneResult("bureau", bu_verdict, bureau.temp, bu_dp, bu_gate),
    }

    # V1 forecast series: indoor_pred simply holds the current reference temp.
    forecast_series = [
        {
            "time_iso": f.time.isoformat(),
            "outdoor": f.temp,
            "indoor_pred": reference.temp,
            "comfort": cfg.comfort_target,
        }
        for f in forecasts
    ]

    peak_outdoor = max((f.temp for f in forecasts), default=None)
    if reference.temp is None or peak_outdoor is None:
        degrees_saved = None
    else:
        degrees_saved = round(max(peak_outdoor - reference.temp, 0.0), 1)

    return Snapshot(
        verdict=verdict,
        reason=_reason_for(verdict, gate_blocking, reference.temp, cfg),
        next_open=next_open,
        next_close=next_close,
        outdoor_temp=outdoor_temp,
        outdoor_dew_point=outdoor_dp,
        indoor_ref_temp=reference.temp,
        humidity_gate_blocking=gate_blocking,
        zones=zones,
        forecast_series=forecast_series,
        degrees_saved=degrees_saved,
    )
