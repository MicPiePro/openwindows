"""Binary sensor platform for the OpenWindows integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import OpenWindowsCoordinator
from .entity import OpenWindowsBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the OpenWindows binary sensors from a config entry."""
    coordinator: OpenWindowsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ACActiveBinarySensor(coordinator, entry),
            HumidityGateBinarySensor(coordinator, entry),
        ]
    )


class ACActiveBinarySensor(OpenWindowsBaseEntity, BinarySensorEntity):
    """On when the portable AC is detected as running."""

    _attr_name = "AC Active"

    def __init__(self, coordinator: OpenWindowsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "ac_active")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.ac_on


class HumidityGateBinarySensor(OpenWindowsBaseEntity, BinarySensorEntity):
    """On when the dew-point humidity gate is blocking an open recommendation."""

    _attr_name = "Humidity Gate"

    def __init__(self, coordinator: OpenWindowsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "humidity_gate")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.humidity_gate_blocking
