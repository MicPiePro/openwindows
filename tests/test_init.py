"""Integration tests for the OpenWindows entrypoint (setup/unload/reload)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openwindows import update_listener
from custom_components.openwindows.const import (
    CONF_BUREAU_HUM,
    CONF_BUREAU_TEMP,
    CONF_CROSSVENT_HUM,
    CONF_CROSSVENT_TEMP,
    CONF_DOOR,
    CONF_ORIENTATION,
    CONF_SOLAR_WEATHER,
    CONF_TEMP_WEATHER,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from custom_components.openwindows.coordinator import OpenWindowsCoordinator

NOTIF = "openwindows_open_close_notification.yaml"
FAN = "openwindows_fan_control.yaml"


def _make_entry(hass, options=None):
    """Build and register a fully-populated config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_TEMP_WEATHER: "weather.home",
            CONF_SOLAR_WEATHER: "weather.maison",
            CONF_CROSSVENT_TEMP: ["sensor.salon_temp"],
            CONF_CROSSVENT_HUM: ["sensor.salon_hum"],
            CONF_BUREAU_TEMP: "sensor.bureau_temp",
            CONF_BUREAU_HUM: "sensor.bureau_hum",
            CONF_DOOR: "binary_sensor.door",
            CONF_ORIENTATION: "S",
        },
        options=options or {},
    )
    entry.add_to_hass(hass)
    return entry


def _forecast_response():
    """Canned weather.get_forecasts response for both weather entities."""
    return {
        "weather.home": {
            "forecast": [
                {
                    "datetime": "2026-07-13T14:00:00+00:00",
                    "temperature": 20.0,
                    "humidity": 50,
                },
                {
                    "datetime": "2026-07-13T15:00:00+00:00",
                    "temperature": 19.0,
                    "humidity": 52,
                },
            ]
        },
        "weather.maison": {
            "forecast": [
                {
                    "datetime": "2026-07-13T14:00:00+00:00",
                    "cloud_coverage": 10,
                    "solar": 800,
                },
                {
                    "datetime": "2026-07-13T15:00:00+00:00",
                    "cloud_coverage": 5,
                    "solar": 850,
                },
            ]
        },
    }


def _patch_forecast_service(hass, response):
    """Patch ServiceRegistry.async_call at the class level.

    `hass.services` is a slotted `ServiceRegistry` instance, so instance-level
    monkeypatching raises `AttributeError`. Patching the class attribute
    achieves the same effect for the lifetime of the `with` block.
    """
    return patch.object(
        type(hass.services), "async_call", AsyncMock(return_value=response)
    )


def _set_sensor_states(hass) -> None:
    """Populate every sensor the coordinator reads so the engine can run."""
    hass.states.async_set("sensor.salon_temp", "30.0")
    hass.states.async_set("sensor.salon_hum", "40")
    hass.states.async_set("sensor.bureau_temp", "28.0")
    hass.states.async_set("sensor.bureau_hum", "45")
    hass.states.async_set("binary_sensor.door", "off")


async def test_async_setup_entry_sets_up_coordinator_and_platforms(hass) -> None:
    """async_setup_entry stores the coordinator, forwards platforms, copies blueprints."""
    entry = _make_entry(hass)
    _set_sensor_states(hass)

    with _patch_forecast_service(hass, _forecast_response()):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert isinstance(coordinator, OpenWindowsCoordinator)
    assert coordinator.last_update_success is True

    # Both platforms (sensor: 8 entities, binary_sensor: 1 entity) forwarded.
    registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(registry, entry.entry_id)
    assert len(entries) == 9

    # Blueprints copied into the HA config dir.
    dest = Path(hass.config.path("blueprints", "automation", "openwindows"))
    assert (dest / NOTIF).is_file()
    assert (dest / FAN).is_file()

    # Options-reload listener registered.
    assert update_listener in entry.update_listeners


async def test_async_unload_entry_tears_down_cleanly(hass) -> None:
    """async_unload_entry unloads platforms and pops the coordinator from hass.data."""
    entry = _make_entry(hass)
    _set_sensor_states(hass)

    with _patch_forecast_service(hass, _forecast_response()):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert entry.entry_id not in hass.data[DOMAIN]


async def test_options_update_triggers_reload_via_update_listener(hass) -> None:
    """Changing entry.options fires the registered update_listener, which reloads."""
    entry = _make_entry(hass)
    _set_sensor_states(hass)

    with _patch_forecast_service(hass, _forecast_response()):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    with patch.object(
        hass.config_entries, "async_reload", AsyncMock(return_value=True)
    ) as mock_reload:
        hass.config_entries.async_update_entry(
            entry, options={CONF_UPDATE_INTERVAL: 30}
        )
        await hass.async_block_till_done()

    mock_reload.assert_awaited_once_with(entry.entry_id)


async def test_async_setup_entry_returns_false_like_behavior_on_bad_forecast(
    hass,
) -> None:
    """If the first refresh fails, async_config_entry_first_refresh raises
    ConfigEntryNotReady and the entry is not marked LOADED."""
    entry = _make_entry(hass)
    _set_sensor_states(hass)
    empty_response = {
        "weather.home": {"forecast": []},
        "weather.maison": {"forecast": []},
    }

    with _patch_forecast_service(hass, empty_response):
        result = await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert result is False
    assert entry.state is ConfigEntryState.SETUP_RETRY
