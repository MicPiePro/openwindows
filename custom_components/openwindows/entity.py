"""Base entities for the OpenWindows integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OpenWindowsCoordinator


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return the single OpenWindows device shared by every entity."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="OpenWindows",
        manufacturer="OpenWindows",
    )


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
        self._attr_device_info = _device_info(entry)


class OpenWindowsDeviceEntity(Entity):
    """Base for entities driven by push callbacks, not by the coordinator.

    Same unique_id/device scheme as ``OpenWindowsBaseEntity``; availability is
    not tied to the coordinator's last update.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, key: str) -> None:
        """Initialize the device entity."""
        self._entry = entry
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = _device_info(entry)
