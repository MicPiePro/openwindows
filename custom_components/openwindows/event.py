"""Event platform for the OpenWindows integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import OpenWindowsCoordinator
from .entity import OpenWindowsDeviceEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the OpenWindows event entities from a config entry."""
    coordinator: OpenWindowsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AiringReminderEvent(coordinator, entry)])


class AiringReminderEvent(OpenWindowsDeviceEntity, EventEntity):
    """Fires when an airing is due (morning, office)."""

    _attr_name = "Airing Reminder"
    _attr_event_types = ["morning", "office"]

    def __init__(self, coordinator: OpenWindowsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(entry, "airing_reminder")
        self._scheduler = coordinator.airing_scheduler

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self._scheduler.async_add_reminder_listener(self._handle_reminder)
        )

    def _handle_reminder(self, slot_key: str, data: dict[str, Any]) -> None:
        self._trigger_event(slot_key, data)
        self.async_write_ha_state()
