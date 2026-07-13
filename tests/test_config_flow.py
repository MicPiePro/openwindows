"""Tests for the OpenWindows config and options flow."""
from __future__ import annotations

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openwindows.const import (
    CONF_AC_POWER,
    CONF_AC_THRESHOLD,
    CONF_BEDROOM_HUM,
    CONF_BEDROOM_TEMP,
    CONF_BUREAU_HUM,
    CONF_BUREAU_TEMP,
    CONF_CLOSE_MARGIN,
    CONF_COMFORT_TARGET,
    CONF_CROSSVENT_HUM,
    CONF_CROSSVENT_TEMP,
    CONF_DOOR,
    CONF_HUMIDITY_GATE,
    CONF_MAX_DEWPOINT,
    CONF_MIN_INDOOR,
    CONF_OPEN_MARGIN,
    CONF_ORIENTATION,
    CONF_SOLAR_WEATHER,
    CONF_TEMP_WEATHER,
    CONF_UPDATE_INTERVAL,
    CONF_VENTILATION,
    CONF_WALL_MASS,
    DOMAIN,
)


@pytest.fixture(autouse=True)
def _enable(enable_custom_integrations):
    """Load the custom_components/openwindows integration for every test."""
    yield


USER_INPUT = {
    CONF_TEMP_WEATHER: "weather.home",
    CONF_SOLAR_WEATHER: "weather.maison",
    CONF_CROSSVENT_TEMP: ["sensor.salon_temp", "sensor.cuisine_temp"],
    CONF_CROSSVENT_HUM: ["sensor.salon_hum", "sensor.cuisine_hum"],
    CONF_BEDROOM_TEMP: ["sensor.chambre_temp", "sensor.chambre_2_temp"],
    CONF_BEDROOM_HUM: ["sensor.chambre_hum"],
    CONF_BUREAU_TEMP: "sensor.bureau_temp",
    CONF_BUREAU_HUM: "sensor.bureau_hum",
    CONF_AC_POWER: "sensor.clim_power",
    CONF_DOOR: "binary_sensor.porte_balcon",
    CONF_ORIENTATION: "SW",
}


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    """The user step stores every selected entity id into entry.data."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] in (None, {})

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "OpenWindows"
    assert result2["data"] == USER_INPUT
    assert result2["options"] == {}

    # Regression (config-flow <-> coordinator seam): the two weather fields must
    # be stored as scalar entity ids, not lists. multiple=True would make the
    # coordinator's `entity_id not in response` raise TypeError on a list.
    assert isinstance(result2["data"][CONF_TEMP_WEATHER], str)
    assert isinstance(result2["data"][CONF_SOLAR_WEATHER], str)


async def test_options_flow_stores_options(hass: HomeAssistant) -> None:
    """The options step writes every tuning key into entry.options."""
    entry = MockConfigEntry(domain=DOMAIN, data=USER_INPUT, options={})
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    options_input = {
        CONF_COMFORT_TARGET: 24.0,
        CONF_OPEN_MARGIN: 2.5,
        CONF_CLOSE_MARGIN: 0.5,
        CONF_MIN_INDOOR: 22.0,
        CONF_HUMIDITY_GATE: False,
        CONF_MAX_DEWPOINT: 17.0,
        CONF_AC_THRESHOLD: 120.0,
        CONF_WALL_MASS: "heavy",
        CONF_VENTILATION: "low",
        CONF_UPDATE_INTERVAL: 30,
    }
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], options_input
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == options_input
    assert entry.options == options_input


async def test_options_flow_defaults_shown(hass: HomeAssistant) -> None:
    """Submitting the form with no changes stores the contract defaults."""
    entry = MockConfigEntry(domain=DOMAIN, data=USER_INPUT, options={})
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={}
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_COMFORT_TARGET] == 25.0
    assert entry.options[CONF_OPEN_MARGIN] == 2.0
    assert entry.options[CONF_CLOSE_MARGIN] == 0.3
    assert entry.options[CONF_MIN_INDOOR] == 23.0
    assert entry.options[CONF_HUMIDITY_GATE] is True
    assert entry.options[CONF_MAX_DEWPOINT] == 18.0
    assert entry.options[CONF_AC_THRESHOLD] == 100.0
    assert entry.options[CONF_WALL_MASS] == "medium"
    assert entry.options[CONF_VENTILATION] == "high"
    assert entry.options[CONF_UPDATE_INTERVAL] == 15
