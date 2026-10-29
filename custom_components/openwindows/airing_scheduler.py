"""Schedules the morning/office airing reminders."""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import dt as dt_util

from .airing import (
    AiringSlot,
    airing_duration_min,
    next_slot,
    weekdays_from_options,
)
from .const import (
    CONF_MORNING_DAYS,
    CONF_MORNING_ENABLED,
    CONF_MORNING_ROOMS,
    CONF_MORNING_TIME,
    CONF_OFFICE_DAYS,
    CONF_OFFICE_ENABLED,
    CONF_OFFICE_ROOMS,
    CONF_OFFICE_TIME,
    DEFAULT_MORNING_DAYS,
    DEFAULT_MORNING_ENABLED,
    DEFAULT_MORNING_ROOMS,
    DEFAULT_MORNING_TIME,
    DEFAULT_OFFICE_DAYS,
    DEFAULT_OFFICE_ENABLED,
    DEFAULT_OFFICE_ROOMS,
    DEFAULT_OFFICE_TIME,
    MODE_AIRING,
)
from .mode_manager import ModeManager

_LOGGER = logging.getLogger(__name__)

# A reminder firing later than this after its slot is dropped as meaningless.
STALE_AFTER = timedelta(minutes=15)


def _slot_from_options(
    cfg: dict, key: str, enabled: tuple, at: tuple, days: tuple, rooms: tuple
) -> AiringSlot:
    """Build one slot; each argument is an ``(option key, default)`` pair."""
    parsed = dt_util.parse_time(str(cfg.get(at[0], at[1])))
    if parsed is None:  # malformed option: fall back to the default time
        parsed = dt_util.parse_time(at[1])
    return AiringSlot(
        key=key,
        enabled=bool(cfg.get(enabled[0], enabled[1])),
        at=parsed,
        weekdays=weekdays_from_options(list(cfg.get(days[0], days[1]))),
        rooms=str(cfg.get(rooms[0], rooms[1])),
    )


def airing_slots_from_options(cfg: dict) -> list[AiringSlot]:
    """Build the morning and office slots from merged entry data/options."""
    return [
        _slot_from_options(
            cfg,
            "morning",
            (CONF_MORNING_ENABLED, DEFAULT_MORNING_ENABLED),
            (CONF_MORNING_TIME, DEFAULT_MORNING_TIME),
            (CONF_MORNING_DAYS, DEFAULT_MORNING_DAYS),
            (CONF_MORNING_ROOMS, DEFAULT_MORNING_ROOMS),
        ),
        _slot_from_options(
            cfg,
            "office",
            (CONF_OFFICE_ENABLED, DEFAULT_OFFICE_ENABLED),
            (CONF_OFFICE_TIME, DEFAULT_OFFICE_TIME),
            (CONF_OFFICE_DAYS, DEFAULT_OFFICE_DAYS),
            (CONF_OFFICE_ROOMS, DEFAULT_OFFICE_ROOMS),
        ),
    ]


class AiringScheduler:
    """Fires a reminder at each configured slot while the mode is airing.

    A timer is kept in every mode: in cooling it fires, sends nothing and
    reschedules, so a later switch to airing needs no re-arming. Starting never
    fires a past slot, because scheduling is strictly after the current time.
    """

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, mode_manager: ModeManager
    ) -> None:
        self.hass = hass
        self.entry = entry
        self._mode_manager = mode_manager
        self._next: tuple[datetime, AiringSlot] | None = None
        self._unsub_timer: Callable[[], None] | None = None
        self._unsub_mode: Callable[[], None] | None = None
        self._listeners: list[Callable[[], None]] = []
        self._reminder_listeners: list[Callable[[str, dict[str, Any]], None]] = []

    # --- read-only state -------------------------------------------------
    @property
    def next_airing(self) -> datetime | None:
        """Next reminder time, or None unless the mode is airing."""
        if self._next is None or self._mode_manager.mode != MODE_AIRING:
            return None
        return self._next[0]

    @property
    def next_slot_key(self) -> str | None:
        """Key of the next reminder's slot, or None unless the mode is airing."""
        if self._next is None or self._mode_manager.mode != MODE_AIRING:
            return None
        return self._next[1].key

    # --- listeners -------------------------------------------------------
    @staticmethod
    def _subscribe(listeners: list, cb: Callable) -> Callable[[], None]:
        listeners.append(cb)

        def _remove() -> None:
            if cb in listeners:
                listeners.remove(cb)

        return _remove

    def async_add_listener(self, cb: Callable[[], None]) -> Callable[[], None]:
        """Register a callback for next-airing changes; return its unsubscribe."""
        return self._subscribe(self._listeners, cb)

    def async_add_reminder_listener(
        self, cb: Callable[[str, dict[str, Any]], None]
    ) -> Callable[[], None]:
        """Register a reminder callback ``(slot_key, data)``; return its unsubscribe."""
        return self._subscribe(self._reminder_listeners, cb)

    def _notify(self) -> None:
        for cb in list(self._listeners):
            cb()

    # --- lifecycle -------------------------------------------------------
    @callback
    def async_start(self) -> None:
        """Schedule the next slot and follow mode changes."""
        if self._unsub_mode is not None:  # idempotent: no duplicate subscription
            self._unsub_mode()
        self._unsub_mode = self._mode_manager.async_add_listener(self._notify)
        self._schedule(dt_util.now())

    @callback
    def async_stop(self) -> None:
        """Cancel the timer and release the mode-manager subscription."""
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None
        if self._unsub_mode is not None:
            self._unsub_mode()
            self._unsub_mode = None
        self._next = None

    # --- scheduling ------------------------------------------------------
    def _schedule(self, after: datetime) -> None:
        """Arm the timer for the first slot strictly after ``after`` (local)."""
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None
        slots = airing_slots_from_options({**self.entry.data, **self.entry.options})
        self._next = next_slot(after, slots)
        if self._next is not None:
            self._unsub_timer = async_track_point_in_time(
                self.hass, self._async_fire, self._next[0]
            )
        self._notify()

    @callback
    def _async_fire(self, _now: datetime) -> None:
        """Send the reminder (airing only) and arm the following slot."""
        self._unsub_timer = None
        if self._next is None:  # stopped between the timer firing and this call
            return
        fired_at, slot = self._next
        now = dt_util.now()
        if (
            self._mode_manager.mode == MODE_AIRING
            and now - fired_at <= STALE_AFTER
        ):
            temp = self._mode_manager.last_outdoor_temp
            data = {
                "rooms": slot.rooms,
                "duration_min": airing_duration_min(temp),
                "outdoor_temp": temp,
            }
            for cb in list(self._reminder_listeners):
                cb(slot.key, data)
        # Reschedule from the later of the fired slot and the clock. The slot
        # guards against a timer firing slightly early picking the same slot
        # again; the clock guards against a stalled loop (host sleep) picking a
        # slot already in the past and replaying a burst of stale reminders.
        self._schedule(max(fired_at, now))
