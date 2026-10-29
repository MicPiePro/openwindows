"""Shared pytest fixtures for the OpenWindows test suite."""

# Import our own namespace package at collection time, before any test creates
# a `hass` fixture instance. `homeassistant.loader.async_setup()` mounts
# `hass.config.config_dir` (which defaults to
# pytest_homeassistant_custom_component's bundled testing_config dir) onto
# sys.path and does a bare `import custom_components`. That bundled dir ships
# a real `custom_components/__init__.py`, so if it wins the `sys.modules`
# cache slot first, `custom_components` is permanently bound to a regular
# (non-namespace) package rooted there, and this repo's
# `custom_components/openwindows` can never be found for the rest of the test
# session. Importing our own `custom_components` here first makes it a PEP
# 420 namespace package instead, whose __path__ recomputes from sys.path on
# each access - so later `hass` fixtures can still mount their own test
# config dir without breaking our import.
import types
from datetime import UTC, datetime

import pytest

import custom_components  # noqa: F401
from custom_components.openwindows.engine import Snapshot, ZoneResult


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of custom integrations in every test."""
    yield


def build_snapshot(**overrides) -> Snapshot:
    """Return a fully populated canned Snapshot, with optional field overrides."""
    forecast_series = [
        {
            "time_iso": "2026-07-13T14:00:00+00:00",
            "outdoor": 30.0,
            "indoor_pred": 27.0,
            "comfort": 25.0,
        },
        {
            "time_iso": "2026-07-13T15:00:00+00:00",
            "outdoor": 31.0,
            "indoor_pred": 28.5,
            "comfort": 25.0,
        },
        {
            "time_iso": "2026-07-13T20:00:00+00:00",
            "outdoor": 22.0,
            "indoor_pred": 26.0,
            "comfort": 25.0,
        },
    ]
    zones = {
        "crossvent": ZoneResult(
            name="crossvent",
            verdict="keep_closed",
            indoor_temp=27.5,
            indoor_dew_point=15.2,
            humidity_gate_blocking=False,
        ),
        "bureau": ZoneResult(
            name="bureau",
            verdict="open",
            indoor_temp=26.0,
            indoor_dew_point=14.0,
            humidity_gate_blocking=False,
        ),
    }
    data = dict(
        verdict="keep_closed",
        reason="Indoor 27.5C above comfort but outdoor not cool enough yet",
        next_open=datetime(2026, 7, 13, 20, 0, tzinfo=UTC),
        next_close=datetime(2026, 7, 14, 7, 0, tzinfo=UTC),
        outdoor_temp=30.0,
        outdoor_dew_point=16.5,
        indoor_ref_temp=27.5,
        humidity_gate_blocking=False,
        zones=zones,
        forecast_series=forecast_series,
        degrees_saved=3.2,
    )
    data.update(overrides)
    return Snapshot(**data)


@pytest.fixture
def fake_coordinator():
    """Return a factory producing a fake coordinator exposing `.data` = Snapshot."""

    def _make(**overrides) -> types.SimpleNamespace:
        return types.SimpleNamespace(data=build_snapshot(**overrides))

    return _make


@pytest.fixture
def fake_entry() -> types.SimpleNamespace:
    """Return a fake config entry exposing only `.entry_id`."""
    return types.SimpleNamespace(entry_id="test_entry")


@pytest.fixture
def forecast_response():
    """Return a factory for a canned ``weather.get_forecasts`` response."""

    def _make(temp: float = 6.0, hours: int = 48) -> dict:
        from datetime import timedelta

        from homeassistant.util import dt as dt_util

        start = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
        return {
            "weather.home": {
                "forecast": [
                    {
                        "datetime": (start + timedelta(hours=i)).isoformat(),
                        "temperature": temp,
                        "humidity": 80,
                    }
                    for i in range(hours)
                ]
            }
        }

    return _make


@pytest.fixture
def loaded_entry(hass, forecast_response):
    """Return an async factory that sets up a full OpenWindows config entry.

    The factory yields ``(entry, coordinator)``. The weather forecast service is
    patched only during setup.
    """
    from unittest.mock import AsyncMock, patch

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.openwindows.const import (
        CONF_BUREAU_HUM,
        CONF_BUREAU_TEMP,
        CONF_CROSSVENT_HUM,
        CONF_CROSSVENT_TEMP,
        CONF_DOOR,
        CONF_ORIENTATION,
        CONF_WEATHER,
        DOMAIN,
    )

    async def _setup(options: dict | None = None):
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
        hass.states.async_set("sensor.salon_temp", "30.0")
        hass.states.async_set("sensor.salon_hum", "40")
        hass.states.async_set("sensor.bureau_temp", "28.0")
        hass.states.async_set("sensor.bureau_hum", "45")
        hass.states.async_set("binary_sensor.door", "off")
        with patch.object(
            type(hass.services),
            "async_call",
            AsyncMock(return_value=forecast_response()),
        ):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
        return entry, hass.data[DOMAIN][entry.entry_id]

    return _setup
