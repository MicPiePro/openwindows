"""Sensor platform for the OpenWindows integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
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
    """Set up the OpenWindows sensors from a config entry."""
    coordinator: OpenWindowsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            VerdictSensor(coordinator, entry),
            NextOpenSensor(coordinator, entry),
            NextCloseSensor(coordinator, entry),
            PredictedIndoorSensor(coordinator, entry),
            CurrentOutdoorSensor(coordinator, entry),
            ZoneCrossventSensor(coordinator, entry),
            ZoneBureauSensor(coordinator, entry),
            DegreesSavedSensor(coordinator, entry),
        ]
    )


class VerdictSensor(OpenWindowsBaseEntity, SensorEntity):
    """Global open/close verdict."""

    _attr_name = "Verdict"

    def __init__(self, coordinator: OpenWindowsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "verdict")

    @property
    def native_value(self) -> str:
        return self.coordinator.data.verdict

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        data = self.coordinator.data
        return {
            "reason": data.reason,
            "outdoor_temp": data.outdoor_temp,
            "indoor_ref_temp": data.indoor_ref_temp,
            "humidity_gate_blocking": data.humidity_gate_blocking,
        }


class NextOpenSensor(OpenWindowsBaseEntity, SensorEntity):
    """Timestamp of the next recommended open."""

    _attr_name = "Next Open"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: OpenWindowsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "next_open")

    @property
    def native_value(self):
        return self.coordinator.data.next_open


class NextCloseSensor(OpenWindowsBaseEntity, SensorEntity):
    """Timestamp of the next recommended close."""

    _attr_name = "Next Close"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: OpenWindowsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "next_close")

    @property
    def native_value(self):
        return self.coordinator.data.next_close


class PredictedIndoorSensor(OpenWindowsBaseEntity, SensorEntity):
    """Peak predicted indoor temperature over the forecast horizon."""

    _attr_name = "Predicted Indoor"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _unrecorded_attributes = frozenset({"forecast"})

    def __init__(self, coordinator: OpenWindowsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "predicted_indoor")

    @property
    def native_value(self) -> float | None:
        preds = [
            f["indoor_pred"]
            for f in self.coordinator.data.forecast_series
            if f.get("indoor_pred") is not None
        ]
        return max(preds) if preds else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {"forecast": self.coordinator.data.forecast_series}


class CurrentOutdoorSensor(OpenWindowsBaseEntity, SensorEntity):
    """Current outdoor temperature used for the decision."""

    _attr_name = "Current Outdoor"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: OpenWindowsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "current_outdoor")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.outdoor_temp

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {"dew_point": self.coordinator.data.outdoor_dew_point}


class ZoneCrossventSensor(OpenWindowsBaseEntity, SensorEntity):
    """Per-zone verdict for the cross-vent core."""

    _attr_name = "Zone Crossvent"

    def __init__(self, coordinator: OpenWindowsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "zone_crossvent")

    @property
    def native_value(self) -> str:
        return self.coordinator.data.zones["crossvent"].verdict

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        zone = self.coordinator.data.zones["crossvent"]
        return {
            "indoor_temp": zone.indoor_temp,
            "indoor_dew_point": zone.indoor_dew_point,
            "humidity_gate_blocking": zone.humidity_gate_blocking,
        }


class ZoneBureauSensor(OpenWindowsBaseEntity, SensorEntity):
    """Per-zone verdict for the bureau."""

    _attr_name = "Zone Bureau"

    def __init__(self, coordinator: OpenWindowsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "zone_bureau")

    @property
    def native_value(self) -> str:
        return self.coordinator.data.zones["bureau"].verdict

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        zone = self.coordinator.data.zones["bureau"]
        return {
            "indoor_temp": zone.indoor_temp,
            "indoor_dew_point": zone.indoor_dew_point,
            "humidity_gate_blocking": zone.humidity_gate_blocking,
        }


class DegreesSavedSensor(OpenWindowsBaseEntity, SensorEntity):
    """Estimated degrees of indoor heat avoided by following the advice."""

    _attr_name = "Degrees Saved"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: OpenWindowsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "degrees_saved")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.degrees_saved
