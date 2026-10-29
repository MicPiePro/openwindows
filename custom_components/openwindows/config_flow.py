"""Config flow for the OpenWindows integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TimeSelector,
)

from .const import (
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
    DEFAULT_HEAT_END_DAYS,
    DEFAULT_HEAT_END_THRESHOLD,
    DEFAULT_HEAT_THRESHOLD,
    DEFAULT_MORNING_DAYS,
    DEFAULT_MORNING_ENABLED,
    DEFAULT_MORNING_ROOMS,
    DEFAULT_MORNING_TIME,
    DEFAULT_OFFICE_DAYS,
    DEFAULT_OFFICE_ENABLED,
    DEFAULT_OFFICE_ROOMS,
    DEFAULT_OFFICE_TIME,
    DEFAULT_WARM_SEASON_END,
    DEFAULT_WARM_SEASON_START,
    DOMAIN,
    ORIENTATION_OPTIONS,
    VENT_OPTIONS,
    WALL_MASS_OPTIONS,
    WEEKDAY_OPTIONS,
)
from .mode import parse_month_day

USER_SCHEMA = vol.Schema(
    {
        # Single-select (scalar entity id): the coordinator calls
        # weather.get_forecasts on this entity and indexes the response by id,
        # so this MUST be a scalar, not a list. See test_config_flow regression.
        vol.Required(CONF_WEATHER): EntitySelector(
            EntitySelectorConfig(domain="weather")
        ),
        vol.Required(CONF_CROSSVENT_TEMP): EntitySelector(
            EntitySelectorConfig(
                domain="sensor", device_class="temperature", multiple=True
            )
        ),
        vol.Required(CONF_CROSSVENT_HUM): EntitySelector(
            EntitySelectorConfig(
                domain="sensor", device_class="humidity", multiple=True
            )
        ),
        vol.Required(CONF_BUREAU_TEMP): EntitySelector(
            EntitySelectorConfig(domain="sensor", device_class="temperature")
        ),
        vol.Required(CONF_BUREAU_HUM): EntitySelector(
            EntitySelectorConfig(domain="sensor", device_class="humidity")
        ),
        vol.Required(CONF_DOOR): EntitySelector(
            EntitySelectorConfig(domain="binary_sensor")
        ),
        vol.Required(CONF_ORIENTATION, default="SW"): SelectSelector(
            SelectSelectorConfig(
                options=ORIENTATION_OPTIONS,
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="orientation",
            )
        ),
    }
)


class OpenWindowsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenWindows."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial configuration step."""
        if user_input is not None:
            return self.async_create_entry(title="OpenWindows", data=user_input)

        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OpenWindowsOptionsFlow:
        """Return the options flow handler."""
        return OpenWindowsOptionsFlow(config_entry)


class OpenWindowsOptionsFlow(OptionsFlow):
    """Handle the OpenWindows tuning options (two steps: init, airing)."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Store the entry so current values can seed the form defaults."""
        self._config_entry = config_entry
        self._init_input: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the tuning and mode options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_init(user_input)
            if not errors:
                self._init_input = {
                    **user_input,
                    CONF_HEAT_END_DAYS: int(user_input[CONF_HEAT_END_DAYS]),
                }
                return await self.async_step_airing()

        defaults = {**self._config_entry.options, **(user_input or {})}
        return self.async_show_form(
            step_id="init",
            data_schema=_init_schema(defaults),
            errors=errors,
        )

    async def async_step_airing(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure the morning and office airing reminders."""
        if user_input is not None:
            return self.async_create_entry(
                title="", data={**self._init_input, **user_input}
            )

        return self.async_show_form(
            step_id="airing",
            data_schema=_airing_schema(self._config_entry.options),
        )


def _validate_init(user_input: dict[str, Any]) -> dict[str, str]:
    """Return form errors for the init step (empty when valid)."""
    try:
        start = parse_month_day(user_input[CONF_WARM_SEASON_START])
        end = parse_month_day(user_input[CONF_WARM_SEASON_END])
    except ValueError:
        return {"base": "invalid_season"}
    if start >= end:
        return {"base": "invalid_season"}
    if user_input[CONF_HEAT_THRESHOLD] <= user_input[CONF_HEAT_END_THRESHOLD]:
        return {"base": "invalid_heat_thresholds"}
    return {}


def _init_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Schema of the init step, seeded from ``defaults``."""
    return vol.Schema(
        {
            vol.Required(
                CONF_COMFORT_TARGET,
                default=defaults.get(CONF_COMFORT_TARGET, 25.0),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=18.0,
                    max=30.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_OPEN_MARGIN,
                default=defaults.get(CONF_OPEN_MARGIN, 2.0),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0.0,
                    max=10.0,
                    step=0.1,
                    unit_of_measurement="°C",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_CLOSE_MARGIN,
                default=defaults.get(CONF_CLOSE_MARGIN, 0.3),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0.0,
                    max=5.0,
                    step=0.1,
                    unit_of_measurement="°C",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_MIN_INDOOR,
                default=defaults.get(CONF_MIN_INDOOR, 23.0),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=15.0,
                    max=28.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_HUMIDITY_GATE,
                default=defaults.get(CONF_HUMIDITY_GATE, True),
            ): BooleanSelector(),
            vol.Required(
                CONF_MAX_DEWPOINT,
                default=defaults.get(CONF_MAX_DEWPOINT, 18.0),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=12.0,
                    max=24.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_WALL_MASS,
                default=defaults.get(CONF_WALL_MASS, "medium"),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=WALL_MASS_OPTIONS,
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="wall_mass",
                )
            ),
            vol.Required(
                CONF_VENTILATION,
                default=defaults.get(CONF_VENTILATION, "high"),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=VENT_OPTIONS,
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="ventilation",
                )
            ),
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=defaults.get(CONF_UPDATE_INTERVAL, 15),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=5,
                    max=120,
                    step=1,
                    unit_of_measurement="min",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_WARM_SEASON_START,
                default=defaults.get(
                    CONF_WARM_SEASON_START, DEFAULT_WARM_SEASON_START
                ),
            ): TextSelector(),
            vol.Required(
                CONF_WARM_SEASON_END,
                default=defaults.get(
                    CONF_WARM_SEASON_END, DEFAULT_WARM_SEASON_END
                ),
            ): TextSelector(),
            vol.Required(
                CONF_HEAT_THRESHOLD,
                default=defaults.get(CONF_HEAT_THRESHOLD, DEFAULT_HEAT_THRESHOLD),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=22.0,
                    max=40.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_HEAT_END_THRESHOLD,
                default=defaults.get(
                    CONF_HEAT_END_THRESHOLD, DEFAULT_HEAT_END_THRESHOLD
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=18.0,
                    max=35.0,
                    step=0.5,
                    unit_of_measurement="°C",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_HEAT_END_DAYS,
                default=defaults.get(CONF_HEAT_END_DAYS, DEFAULT_HEAT_END_DAYS),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=7,
                    step=1,
                    unit_of_measurement="d",
                    mode=NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _slot_fields(
    defaults: dict[str, Any],
    *,
    enabled: tuple[str, bool],
    at: tuple[str, str],
    days: tuple[str, list[str]],
    rooms: tuple[str, str],
) -> dict[Any, Any]:
    """Schema fields of one airing slot (enabled, time, days, rooms)."""
    return {
        vol.Required(
            enabled[0], default=defaults.get(enabled[0], enabled[1])
        ): BooleanSelector(),
        vol.Required(at[0], default=defaults.get(at[0], at[1])): TimeSelector(),
        vol.Required(
            days[0], default=list(defaults.get(days[0], days[1]))
        ): SelectSelector(
            SelectSelectorConfig(
                options=WEEKDAY_OPTIONS,
                multiple=True,
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="weekday",
            )
        ),
        vol.Required(rooms[0], default=defaults.get(rooms[0], rooms[1])): TextSelector(),
    }


def _airing_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Schema of the airing step, seeded from ``defaults``."""
    return vol.Schema(
        {
            **_slot_fields(
                defaults,
                enabled=(CONF_MORNING_ENABLED, DEFAULT_MORNING_ENABLED),
                at=(CONF_MORNING_TIME, DEFAULT_MORNING_TIME),
                days=(CONF_MORNING_DAYS, DEFAULT_MORNING_DAYS),
                rooms=(CONF_MORNING_ROOMS, DEFAULT_MORNING_ROOMS),
            ),
            **_slot_fields(
                defaults,
                enabled=(CONF_OFFICE_ENABLED, DEFAULT_OFFICE_ENABLED),
                at=(CONF_OFFICE_TIME, DEFAULT_OFFICE_TIME),
                days=(CONF_OFFICE_DAYS, DEFAULT_OFFICE_DAYS),
                rooms=(CONF_OFFICE_ROOMS, DEFAULT_OFFICE_ROOMS),
            ),
        }
    )


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
