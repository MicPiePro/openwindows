"""Cooling/airing mode state, temporary override and persistence."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_HEAT_END_DAYS,
    CONF_HEAT_END_THRESHOLD,
    CONF_HEAT_THRESHOLD,
    CONF_WARM_SEASON_END,
    CONF_WARM_SEASON_START,
    DEFAULT_HEAT_END_DAYS,
    DEFAULT_HEAT_END_THRESHOLD,
    DEFAULT_HEAT_THRESHOLD,
    DEFAULT_OVERRIDE_DAYS,
    DEFAULT_WARM_SEASON_END,
    DEFAULT_WARM_SEASON_START,
    DOMAIN,
    MODE_AIRING,
    MODE_COOLING,
    OVERRIDE_AUTO,
    OVERRIDE_FORCE_AIRING,
    OVERRIDE_FORCE_COOLING,
    OVERRIDE_OPTIONS,
)
from .engine import HourForecast
from .mode import (
    ModeConfig,
    ModeState,
    decide_auto_mode,
    in_warm_season,
    max_within,
    parse_month_day,
)

STORAGE_VERSION = 1

_FORCED_MODES = {
    OVERRIDE_FORCE_COOLING: MODE_COOLING,
    OVERRIDE_FORCE_AIRING: MODE_AIRING,
}


def mode_config_from_options(cfg: dict) -> ModeConfig:
    """Build a ModeConfig from merged entry data/options (defaults when absent)."""
    return ModeConfig(
        warm_season_start=parse_month_day(
            str(cfg.get(CONF_WARM_SEASON_START, DEFAULT_WARM_SEASON_START))
        ),
        warm_season_end=parse_month_day(
            str(cfg.get(CONF_WARM_SEASON_END, DEFAULT_WARM_SEASON_END))
        ),
        heat_threshold=float(cfg.get(CONF_HEAT_THRESHOLD, DEFAULT_HEAT_THRESHOLD)),
        heat_end_threshold=float(
            cfg.get(CONF_HEAT_END_THRESHOLD, DEFAULT_HEAT_END_THRESHOLD)
        ),
        heat_end_days=int(cfg.get(CONF_HEAT_END_DAYS, DEFAULT_HEAT_END_DAYS)),
    )


def _aware(value: datetime) -> datetime:
    """Return a timezone-aware datetime (naive values are read as local time)."""
    return value if value.tzinfo is not None else dt_util.as_local(value)


def _parse_dt(value: Any) -> datetime | None:
    """Parse a stored ISO string to an aware datetime, or None."""
    if not isinstance(value, str):
        return None
    parsed = dt_util.parse_datetime(value)
    return _aware(parsed) if parsed is not None else None


class ModeManager:
    """Owns the automatic mode, the temporary override and their persistence."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._store: Store = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}.mode"
        )
        self._state = ModeState()
        self._reason = "no_forecast"
        self._override_option = OVERRIDE_AUTO
        self._override_until: datetime | None = None
        self._override_days = DEFAULT_OVERRIDE_DAYS
        self._max_48h: float | None = None
        self._last_outdoor_temp: float | None = None
        self._in_warm_season = in_warm_season(dt_util.now().date(), self._config())
        self._last_saved: dict[str, Any] | None = None
        self._listeners: list[Callable[[], None]] = []

    # --- configuration ---------------------------------------------------
    def _config(self) -> ModeConfig:
        return mode_config_from_options({**self.entry.data, **self.entry.options})

    # --- read-only state -------------------------------------------------
    @property
    def _override_active(self) -> bool:
        return self._override_option in _FORCED_MODES

    @property
    def mode(self) -> str:
        if self._override_active:
            return _FORCED_MODES[self._override_option]
        return self._state.mode or MODE_AIRING

    @property
    def source(self) -> str:
        return "override" if self._override_active else "auto"

    @property
    def override_option(self) -> str:
        return self._override_option

    @property
    def override_until(self) -> datetime | None:
        return self._override_until

    @property
    def override_days(self) -> int:
        return self._override_days

    @property
    def reason(self) -> str:
        return "override" if self._override_active else self._reason

    @property
    def max_48h(self) -> float | None:
        return self._max_48h

    @property
    def in_warm_season(self) -> bool:
        return self._in_warm_season

    @property
    def last_outdoor_temp(self) -> float | None:
        return self._last_outdoor_temp

    # --- listeners -------------------------------------------------------
    def async_add_listener(self, cb: Callable[[], None]) -> Callable[[], None]:
        """Register a change callback; return the unsubscribe function."""
        self._listeners.append(cb)

        def _remove() -> None:
            if cb in self._listeners:
                self._listeners.remove(cb)

        return _remove

    def _notify(self) -> None:
        for cb in list(self._listeners):
            cb()

    # --- persistence -----------------------------------------------------
    def _payload(self) -> dict[str, Any]:
        since = self._state.heat_end_since
        return {
            "auto_mode": self._state.mode,
            "heat_end_since": since.isoformat() if since else None,
            "override_option": self._override_option,
            "override_until": (
                self._override_until.isoformat() if self._override_until else None
            ),
            "override_days": self._override_days,
            "reason": self._reason,
        }

    async def _async_save(self) -> None:
        """Write the Store, skipping the write when nothing changed."""
        payload = self._payload()
        if payload == self._last_saved:
            return
        await self._store.async_save(payload)
        self._last_saved = payload

    async def async_load(self) -> None:
        """Restore the persisted state; an expired override reverts to auto."""
        data = await self._store.async_load()
        if not data:
            return
        self._last_saved = data
        self._state = ModeState(
            mode=data.get("auto_mode"),
            heat_end_since=_parse_dt(data.get("heat_end_since")),
        )
        self._reason = data.get("reason") or self._reason
        days = data.get("override_days")
        if isinstance(days, (int, float)) and days >= 1:
            self._override_days = int(days)
        option = data.get("override_option")
        until = _parse_dt(data.get("override_until"))
        if option in _FORCED_MODES and until is not None:
            if until > dt_util.now():
                self._override_option = option
                self._override_until = until
            else:
                await self._async_save()  # drop the stale override on disk

    # --- operations ------------------------------------------------------
    async def async_update(
        self, now_local: datetime, forecasts: list[HourForecast] | None
    ) -> None:
        """Re-evaluate the automatic mode and expire a finished override."""
        now_local = _aware(now_local)
        cfg = self._config()
        if self._override_until is not None and now_local >= self._override_until:
            self._override_option = OVERRIDE_AUTO
            self._override_until = None
        self._max_48h = max_within(forecasts, now_local) if forecasts else None
        self._state, self._reason = decide_auto_mode(
            now_local, self._max_48h, self._state, cfg
        )
        self._in_warm_season = in_warm_season(now_local.date(), cfg)
        self._last_outdoor_temp = forecasts[0].temp if forecasts else None
        await self._async_save()
        self._notify()

    async def async_set_override(self, option: str, now_local: datetime) -> None:
        """Force a mode for ``override_days`` days, or clear it with ``auto``."""
        if option not in OVERRIDE_OPTIONS:
            raise ValueError(f"Unknown override option {option!r}")
        if option == OVERRIDE_AUTO:
            self._override_option = OVERRIDE_AUTO
            self._override_until = None
        else:
            self._override_option = option
            self._override_until = _aware(now_local) + timedelta(
                days=self._override_days
            )
        await self._async_save()
        self._notify()

    async def async_set_override_days(self, days: int) -> None:
        """Set the duration of future overrides; a running one is unchanged."""
        self._override_days = int(days)
        await self._async_save()
        self._notify()
