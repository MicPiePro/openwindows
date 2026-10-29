"""Number platform for the OpenWindows integration."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
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
    """Set up the OpenWindows number entities from a config entry."""
    coordinator: OpenWindowsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([OverrideDaysNumber(coordinator, entry)])


class OverrideDaysNumber(OpenWindowsDeviceEntity, NumberEntity):
    """Duration, in days, of the next manual mode override."""

    _attr_name = "Override Days"
    _attr_native_min_value = 1
    _attr_native_max_value = 14
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_mode = NumberMode.BOX
    _attr_translation_key = "override_days"

    def __init__(self, coordinator: OpenWindowsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(entry, "override_days")
        self._manager = coordinator.mode_manager

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self._manager.async_add_listener(self.async_write_ha_state)
        )

    @property
    def native_value(self) -> int:
        return self._manager.override_days

    async def async_set_native_value(self, value: float) -> None:
        await self._manager.async_set_override_days(int(value))
