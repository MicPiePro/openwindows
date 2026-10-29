"""Tests for the OpenWindows DataUpdateCoordinator."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openwindows.const import (
    CONF_BUREAU_HUM,
    CONF_BUREAU_TEMP,
    CONF_CROSSVENT_HUM,
    CONF_CROSSVENT_TEMP,
    CONF_DOOR,
    CONF_ORIENTATION,
    CONF_UPDATE_INTERVAL,
    CONF_WEATHER,
    DOMAIN,
    OVERRIDE_FORCE_AIRING,
    OVERRIDE_FORCE_COOLING,
    VERDICT_CLOSE,
    VERDICT_INACTIVE,
    VERDICT_OPEN,
)
from custom_components.openwindows.coordinator import OpenWindowsCoordinator
from custom_components.openwindows.engine import EngineConfig, run_decision_engine

NOW = datetime(2026, 7, 13, 15, 0, tzinfo=ZoneInfo("Europe/Paris"))


@contextmanager
def _frozen_july():
    """Pin local and UTC time to 2026-07-13 15:00 Paris (warm season)."""
    with (
        patch("custom_components.openwindows.coordinator.dt_util.now", return_value=NOW),
        patch(
            "custom_components.openwindows.coordinator.dt_util.utcnow",
            return_value=NOW.astimezone(dt_util.UTC),
        ),
    ):
        yield


def _heat_forecast_response():
    """Cool now, but a 30 C peak tomorrow: Cooling mode, verdict still `open`."""
    resp = _forecast_response()
    resp["weather.home"]["forecast"].append(
        {
            "datetime": "2026-07-14T14:00:00+00:00",
            "temperature": 30.0,
            "humidity": 40,
            "cloud_coverage": 0,
        }
    )
    return resp


def _hot_indoors(hass) -> None:
    hass.states.async_set("sensor.salon_temp", "30.0")
    hass.states.async_set("sensor.salon_hum", "40")
    hass.states.async_set("sensor.bureau_temp", "28.0")
    hass.states.async_set("sensor.bureau_hum", "45")
    hass.states.async_set("binary_sensor.door", "off")


def _make_entry(hass, options=None):
    """Build and register a fully-populated config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_WEATHER: "weather.home",
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
    """Canned weather.get_forecasts response for the single weather entity."""
    return {
        "weather.home": {
            "forecast": [
                {
                    "datetime": "2026-07-13T14:00:00+00:00",
                    "temperature": 20.0,
                    "humidity": 50,
                    "cloud_coverage": 10,
                },
                {
                    "datetime": "2026-07-13T15:00:00+00:00",
                    "temperature": 19.0,
                    "humidity": 52,
                    "cloud_coverage": 5,
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


async def test_parse_forecasts_computes_dew_point_and_reads_cloud_cover(hass):
    entry = _make_entry(hass)
    coordinator = OpenWindowsCoordinator(hass, entry)
    resp = _forecast_response()
    fc = resp["weather.home"]["forecast"]

    hours = coordinator._parse_forecasts(fc)

    assert len(hours) == 2
    first = hours[0]
    assert first.temp == 20.0
    assert first.humidity == 50
    # dew point computed from temp+humidity via Magnus (approx 9.3 C)
    assert first.dew_point is not None
    assert 9.0 < first.dew_point < 9.6
    # cloud cover read from the same forecast item (Open-Meteo-style payload)
    assert first.cloud_cover == 10
    # HA's weather.get_forecasts hourly items don't carry a raw solar field
    assert first.solar is None


async def test_parse_forecasts_dew_point_none_without_humidity(hass):
    entry = _make_entry(hass)
    coordinator = OpenWindowsCoordinator(hass, entry)
    fc = [{"datetime": "2026-07-13T14:00:00+00:00", "temperature": 22.0}]
    hours = coordinator._parse_forecasts(fc)
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
    # A 30 C peak in the window keeps Cooling mode (v0.3.0 behaviour).
    with _frozen_july(), _patch_forecast_service(hass, _heat_forecast_response()):
        await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert coordinator.data.verdict == VERDICT_OPEN


async def test_update_data_raises_when_no_forecast(hass):
    entry = _make_entry(hass)
    coordinator = OpenWindowsCoordinator(hass, entry)
    empty_response = {
        "weather.home": {"forecast": []},
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


async def test_airing_mode_suppresses_verdict(hass):
    entry = _make_entry(hass)
    _hot_indoors(hass)
    coordinator = OpenWindowsCoordinator(hass, entry)
    # Canned forecast peaks at 20 C: no heat, first boot -> Airing.
    with _frozen_july(), _patch_forecast_service(hass, _forecast_response()):
        await coordinator.async_refresh()

    assert coordinator.mode_manager.mode == "airing"
    assert coordinator.data.verdict == VERDICT_INACTIVE
    assert coordinator.data.next_open is None


async def test_heat_keeps_v030_behaviour(hass):
    entry = _make_entry(hass)
    _hot_indoors(hass)
    coordinator = OpenWindowsCoordinator(hass, entry)
    with _frozen_july(), _patch_forecast_service(hass, _heat_forecast_response()):
        await coordinator.async_refresh()
        expected = run_decision_engine(
            dt_util.utcnow(),
            coordinator._parse_forecasts(
                _heat_forecast_response()["weather.home"]["forecast"]
            ),
            coordinator._read_zone(
                "crossvent", ["sensor.salon_temp"], ["sensor.salon_hum"]
            ),
            coordinator._read_zone("bureau", "sensor.bureau_temp", "sensor.bureau_hum"),
            False,
            EngineConfig(),
        )

    assert coordinator.mode_manager.mode == "cooling"
    assert coordinator.data == expected
    assert coordinator.data.verdict == VERDICT_OPEN


async def test_switch_to_airing_while_open_publishes_close_once(hass):
    entry = _make_entry(hass)
    _hot_indoors(hass)
    coordinator = OpenWindowsCoordinator(hass, entry)
    with _frozen_july(), _patch_forecast_service(hass, _heat_forecast_response()):
        await coordinator.async_refresh()
        assert coordinator.data.verdict == VERDICT_OPEN

        await coordinator.mode_manager.async_set_override(OVERRIDE_FORCE_AIRING, NOW)
        await coordinator.async_refresh()
        assert coordinator.data.verdict == VERDICT_CLOSE
        assert coordinator.data.reason == "mode_change"

        await coordinator.async_refresh()
        assert coordinator.data.verdict == VERDICT_INACTIVE
        assert coordinator.data.reason == "airing_mode"


async def test_forecast_failure_still_updates_mode_manager(hass):
    entry = _make_entry(hass)
    coordinator = OpenWindowsCoordinator(hass, entry)
    with _frozen_july(), _patch_forecast_service(hass, {}):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

    assert coordinator.mode_manager.reason == "no_forecast"


async def test_forecast_service_error_still_updates_mode_manager(hass):
    """weather.get_forecasts raising (entity unavailable) must not skip the manager."""
    entry = _make_entry(hass)
    coordinator = OpenWindowsCoordinator(hass, entry)
    # An override that expired a day ago must still be cleared.
    await coordinator.mode_manager.async_set_override(
        OVERRIDE_FORCE_COOLING, NOW - timedelta(days=2)
    )
    assert coordinator.mode_manager.override_option == OVERRIDE_FORCE_COOLING

    with (
        _frozen_july(),
        patch.object(
            type(hass.services),
            "async_call",
            AsyncMock(side_effect=HomeAssistantError("no entity matched")),
        ),
    ):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

    manager = coordinator.mode_manager
    assert manager.override_option == "auto"
    assert manager.reason == "no_forecast"
    assert manager.last_outdoor_temp is None
