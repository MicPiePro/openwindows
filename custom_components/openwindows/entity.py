"""Base entity for the OpenWindows integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OpenWindowsCoordinator


class OpenWindowsBaseEntity(CoordinatorEntity[OpenWindowsCoordinator]):
    """Base class wiring every OpenWindows entity to the coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OpenWindowsCoordinator,
        entry: ConfigEntry,
        key: str,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="OpenWindows",
            manufacturer="OpenWindows",
        )
