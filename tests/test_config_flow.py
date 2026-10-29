"""Tests for the OpenWindows config and options flow."""
from __future__ import annotations

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openwindows.const import (
    CONF_BUREAU_HUM,
    CONF_BUREAU_TEMP,
    CONF_CLOSE_MARGIN,
    CONF_COMFORT_TARGET,
    CONF_CROSSVENT_HUM,
    CONF_CROSSVENT_TEMP,
    CONF_DOOR,
    CONF_HEAT_END_DAYS,
    CONF_HEAT_END_THRESHOLD,
    CONF_HEAT_THRESHOLD,
    CONF_HUMIDITY_GATE,
    CONF_MAX_DEWPOINT,
    CONF_MIN_INDOOR,
    CONF_MORNING_DAYS,
    CONF_MORNING_ENABLED,
    CONF_MORNING_ROOMS,
    CONF_MORNING_TIME,
    CONF_OFFICE_DAYS,
    CONF_OFFICE_ENABLED,
    CONF_OFFICE_ROOMS,
    CONF_OFFICE_TIME,
    CONF_OPEN_MARGIN,
    CONF_ORIENTATION,
    CONF_UPDATE_INTERVAL,
    CONF_VENTILATION,
    CONF_WALL_MASS,
    CONF_WARM_SEASON_END,
    CONF_WARM_SEASON_START,
    CONF_WEATHER,
    DOMAIN,
)


@pytest.fixture(autouse=True)
def _enable(enable_custom_integrations):
    """Load the custom_components/openwindows integration for every test."""
    yield


USER_INPUT = {
    CONF_WEATHER: "weather.home",
    CONF_CROSSVENT_TEMP: ["sensor.salon_temp", "sensor.cuisine_temp"],
    CONF_CROSSVENT_HUM: ["sensor.salon_hum", "sensor.cuisine_hum"],
    CONF_BUREAU_TEMP: "sensor.bureau_temp",
    CONF_BUREAU_HUM: "sensor.bureau_hum",
    CONF_DOOR: "binary_sensor.porte_balcon",
    CONF_ORIENTATION: "SW",
}


MODE_INPUT = {
    CONF_WARM_SEASON_START: "05-01",
    CONF_WARM_SEASON_END: "09-30",
    CONF_HEAT_THRESHOLD: 30.0,
    CONF_HEAT_END_THRESHOLD: 26.0,
    CONF_HEAT_END_DAYS: 3,
}

AIRING_INPUT = {
    CONF_MORNING_ENABLED: False,
    CONF_MORNING_TIME: "07:30:00",
    CONF_MORNING_DAYS: ["sat", "sun"],
    CONF_MORNING_ROOMS: "Salon",
    CONF_OFFICE_ENABLED: True,
    CONF_OFFICE_TIME: "10:00:00",
    CONF_OFFICE_DAYS: ["mon", "tue"],
    CONF_OFFICE_ROOMS: "Bureau et chambre",
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

    # Regression (config-flow <-> coordinator seam): the weather field must be
    # stored as a scalar entity id, not a list. multiple=True would make the
    # coordinator's `entity_id not in response` raise TypeError on a list.
    assert isinstance(result2["data"][CONF_WEATHER], str)


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
        CONF_WALL_MASS: "heavy",
        CONF_VENTILATION: "low",
        CONF_UPDATE_INTERVAL: 30,
    }
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], {**options_input, **MODE_INPUT}
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "airing"
    result3 = await hass.config_entries.options.async_configure(
        result["flow_id"], AIRING_INPUT
    )
    await hass.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["data"] == {**options_input, **MODE_INPUT, **AIRING_INPUT}
    assert entry.options == {**options_input, **MODE_INPUT, **AIRING_INPUT}


async def test_options_flow_defaults_shown(hass: HomeAssistant) -> None:
    """Submitting the form with no changes stores the contract defaults."""
    entry = MockConfigEntry(domain=DOMAIN, data=USER_INPUT, options={})
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={}
    )
    assert result2["step_id"] == "airing"
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
    assert entry.options[CONF_WALL_MASS] == "medium"
    assert entry.options[CONF_VENTILATION] == "high"
    assert entry.options[CONF_UPDATE_INTERVAL] == 15
    assert entry.options[CONF_WARM_SEASON_START] == "04-01"
    assert entry.options[CONF_WARM_SEASON_END] == "10-31"
    assert entry.options[CONF_HEAT_THRESHOLD] == 28.0
    assert entry.options[CONF_HEAT_END_THRESHOLD] == 25.0
    assert entry.options[CONF_HEAT_END_DAYS] == 2
    assert entry.options[CONF_MORNING_ENABLED] is True
    assert entry.options[CONF_MORNING_TIME] == "08:00:00"
    assert entry.options[CONF_MORNING_DAYS] == [
        "mon", "tue", "wed", "thu", "fri", "sat", "sun"
    ]
    assert entry.options[CONF_MORNING_ROOMS] == "Chambre et salon"
    assert entry.options[CONF_OFFICE_ENABLED] is True
    assert entry.options[CONF_OFFICE_TIME] == "09:20:00"
    assert entry.options[CONF_OFFICE_DAYS] == ["mon", "tue", "wed", "thu", "fri"]
    assert entry.options[CONF_OFFICE_ROOMS] == "Bureau"


async def test_options_two_steps_saves_flat_options(hass: HomeAssistant) -> None:
    """init then airing: mode fields and slots land flat in entry.options."""
    entry = MockConfigEntry(domain=DOMAIN, data=USER_INPUT, options={})
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_HEAT_THRESHOLD: 28.0, CONF_HEAT_END_DAYS: 2.0}
    )
    assert result["step_id"] == "airing"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_HEAT_THRESHOLD] == 28.0
    assert entry.options[CONF_OFFICE_DAYS] == ["mon", "tue", "wed", "thu", "fri"]
    assert entry.options[CONF_HEAT_END_DAYS] == 2
    assert isinstance(entry.options[CONF_HEAT_END_DAYS], int)


async def test_options_prefill_from_current_options(hass: HomeAssistant) -> None:
    """The airing step defaults come from the stored options."""
    entry = MockConfigEntry(
        domain=DOMAIN, data=USER_INPUT, options={CONF_OFFICE_ROOMS: "Atelier"}
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    await hass.config_entries.options.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert entry.options[CONF_OFFICE_ROOMS] == "Atelier"


@pytest.mark.parametrize(
    ("start", "end"),
    [("13-01", "10-31"), ("04-01", "xx"), ("11-01", "04-01"), ("04-01", "04-01")],
)
async def test_options_invalid_season(
    hass: HomeAssistant, start: str, end: str
) -> None:
    """A bad or inverted warm season re-shows init with invalid_season."""
    entry = MockConfigEntry(domain=DOMAIN, data=USER_INPUT, options={})
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_WARM_SEASON_START: start, CONF_WARM_SEASON_END: end},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] == {"base": "invalid_season"}


async def test_options_invalid_heat_thresholds(hass: HomeAssistant) -> None:
    """Heat threshold must be strictly above the heat-end threshold."""
    entry = MockConfigEntry(domain=DOMAIN, data=USER_INPUT, options={})
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_HEAT_THRESHOLD: 28.0, CONF_HEAT_END_THRESHOLD: 28.0}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] == {"base": "invalid_heat_thresholds"}
