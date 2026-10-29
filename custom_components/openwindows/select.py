"""Select platform for the OpenWindows integration."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, OVERRIDE_OPTIONS
from .coordinator import OpenWindowsCoordinator
from .entity import OpenWindowsDeviceEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the OpenWindows select entities from a config entry."""
    coordinator: OpenWindowsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ModeOverrideSelect(coordinator, entry)])


class ModeOverrideSelect(OpenWindowsDeviceEntity, SelectEntity):
    """Manually force cooling or airing mode for a limited time."""

    _attr_name = "Mode Override"
    _attr_options = OVERRIDE_OPTIONS
    _attr_translation_key = "mode_override"

    def __init__(self, coordinator: OpenWindowsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(entry, "mode_override")
        self._coordinator = coordinator
        self._manager = coordinator.mode_manager

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self._manager.async_add_listener(self.async_write_ha_state)
        )

    @property
    def current_option(self) -> str:
        return self._manager.override_option

    async def async_select_option(self, option: str) -> None:
        await self._manager.async_set_override(option, dt_util.now())
        await self._coordinator.async_request_refresh()
