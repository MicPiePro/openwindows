"""Tests for the OpenWindows DataUpdateCoordinator."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

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
    VERDICT_OPEN,
)
from custom_components.openwindows.coordinator import OpenWindowsCoordinator


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


async def test_update_interval_default(hass):
    entry = _make_entry(hass)
    coordinator = OpenWindowsCoordinator(hass, entry)
    assert coordinator.update_interval == timedelta(minutes=15)


async def test_update_interval_from_options(hass):
    entry = _make_entry(hass, options={CONF_UPDATE_INTERVAL: 30})
    coordinator = OpenWindowsCoordinator(hass, entry)
    assert coordinator.update_interval == timedelta(minutes=30)


async def test_state_float_handles_unavailable(hass):
    entry = _make_entry(hass)
    coordinator = OpenWindowsCoordinator(hass, entry)
    hass.states.async_set("sensor.a", "unavailable")
    assert coordinator._state_float("sensor.a") is None
    assert coordinator._state_float(None) is None
    hass.states.async_set("sensor.a", "21.5")
    assert coordinator._state_float("sensor.a") == 21.5


async def test_read_zone_max(hass):
    entry = _make_entry(hass)
    coordinator = OpenWindowsCoordinator(hass, entry)
    hass.states.async_set("sensor.a", "20.0")
    hass.states.async_set("sensor.b", "30.0")
    reading = coordinator._read_zone("crossvent", ["sensor.a", "sensor.b"], [])
    assert reading.name == "crossvent"
    assert reading.temp == 30.0
    assert reading.humidity is None


async def test_parse_forecasts_merges_and_computes_dew_point(hass):
    entry = _make_entry(hass)
    coordinator = OpenWindowsCoordinator(hass, entry)
    resp = _forecast_response()
    temp_fc = resp["weather.home"]["forecast"]
    solar_fc = resp["weather.maison"]["forecast"]

    hours = coordinator._parse_forecasts(temp_fc, solar_fc)

    assert len(hours) == 2
    first = hours[0]
    assert first.temp == 20.0
    assert first.humidity == 50
    # dew point computed from temp+humidity via Magnus (approx 9.3 C)
    assert first.dew_point is not None
    assert 9.0 < first.dew_point < 9.6
    # cloud + solar pulled from the solar weather source by index
    assert first.cloud_cover == 10
    assert first.solar == 800


async def test_parse_forecasts_dew_point_none_without_humidity(hass):
    entry = _make_entry(hass)
    coordinator = OpenWindowsCoordinator(hass, entry)
    temp_fc = [{"datetime": "2026-07-13T14:00:00+00:00", "temperature": 22.0}]
    hours = coordinator._parse_forecasts(temp_fc, [])
    assert len(hours) == 1
    assert hours[0].humidity is None
    assert hours[0].dew_point is None
    assert hours[0].cloud_cover is None
    assert hours[0].solar is None


def _patch_forecast_service(hass, response):
    """Patch ServiceRegistry.async_call at the class level.

    `hass.services` is a slotted `ServiceRegistry` instance (`__slots__ =
    ("_hass", "_services")`), so instance-level monkeypatching
    (`hass.services.async_call = AsyncMock(...)`) raises `AttributeError:
    'ServiceRegistry' object attribute 'async_call' is read-only` on this HA
    version. Patching the class attribute achieves the same effect (control
    what `weather.get_forecasts` returns) for the lifetime of the `with` block.
    """
    return patch.object(
        type(hass.services), "async_call", AsyncMock(return_value=response)
    )


async def test_update_data_verdict_open(hass):
    entry = _make_entry(hass)
    # Hot indoors, cool outdoors, door closed -> engine should say OPEN.
    hass.states.async_set("sensor.salon_temp", "30.0")
    hass.states.async_set("sensor.salon_hum", "40")
    hass.states.async_set("sensor.bureau_temp", "28.0")
    hass.states.async_set("sensor.bureau_hum", "45")
    hass.states.async_set("binary_sensor.door", "off")

    coordinator = OpenWindowsCoordinator(hass, entry)
    with _patch_forecast_service(hass, _forecast_response()):
        await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert coordinator.data.verdict == VERDICT_OPEN


async def test_update_data_raises_when_no_forecast(hass):
    entry = _make_entry(hass)
    coordinator = OpenWindowsCoordinator(hass, entry)
    empty_response = {
        "weather.home": {"forecast": []},
        "weather.maison": {"forecast": []},
    }
    with _patch_forecast_service(hass, empty_response):
        await coordinator.async_refresh()

    assert coordinator.last_update_success is False


async def test_setup_forecast_triggers_requests_refresh(hass):
    entry = _make_entry(hass)
    coordinator = OpenWindowsCoordinator(hass, entry)
    coordinator.async_request_refresh = AsyncMock()

    coordinator.async_setup_forecast_triggers()

    # A state change on a tracked weather entity should schedule a refresh.
    hass.states.async_set("weather.home", "sunny")
    await hass.async_block_till_done()

    assert coordinator.async_request_refresh.called
    # The unsubscribe callback is registered for cleanup on unload.
    # (`MockConfigEntry.async_on_unload` is the real `ConfigEntry` method, not
    # a Mock, so we check the real `_on_unload` list it appends to rather than
    # a `.called` attribute that only exists on mocks.)
    assert entry._on_unload is not None and len(entry._on_unload) >= 1
