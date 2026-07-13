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
)

from .const import (
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
    CONF_DEWPOINT_MARGIN,
    CONF_DOOR,
    CONF_HUMIDITY_GATE,
    CONF_MIN_INDOOR,
    CONF_OPEN_MARGIN,
    CONF_ORIENTATION,
    CONF_SOLAR_WEATHER,
    CONF_TEMP_WEATHER,
    CONF_UPDATE_INTERVAL,
    CONF_VENTILATION,
    CONF_WALL_MASS,
    DOMAIN,
    ORIENTATION_OPTIONS,
    VENT_OPTIONS,
    WALL_MASS_OPTIONS,
)

USER_SCHEMA = vol.Schema(
    {
        # Single-select (scalar entity id): the coordinator calls
        # weather.get_forecasts per entity and indexes the response by id,
        # so these MUST be scalars, not lists. See test_config_flow regression.
        vol.Required(CONF_TEMP_WEATHER): EntitySelector(
            EntitySelectorConfig(domain="weather")
        ),
        vol.Required(CONF_SOLAR_WEATHER): EntitySelector(
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
        vol.Required(CONF_BEDROOM_TEMP): EntitySelector(
            EntitySelectorConfig(
                domain="sensor", device_class="temperature", multiple=True
            )
        ),
        vol.Required(CONF_BEDROOM_HUM): EntitySelector(
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
        vol.Required(CONF_AC_POWER): EntitySelector(
            EntitySelectorConfig(domain="sensor", device_class="power")
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
    """Handle the OpenWindows tuning options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Store the entry so current values can seed the form defaults."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the tuning options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self._config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_COMFORT_TARGET,
                    default=options.get(CONF_COMFORT_TARGET, 25.0),
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
                    default=options.get(CONF_OPEN_MARGIN, 2.0),
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
                    default=options.get(CONF_CLOSE_MARGIN, 0.3),
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
                    default=options.get(CONF_MIN_INDOOR, 23.0),
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
                    default=options.get(CONF_HUMIDITY_GATE, True),
                ): BooleanSelector(),
                vol.Required(
                    CONF_DEWPOINT_MARGIN,
                    default=options.get(CONF_DEWPOINT_MARGIN, 1.0),
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
                    CONF_AC_THRESHOLD,
                    default=options.get(CONF_AC_THRESHOLD, 100.0),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.0,
                        max=3000.0,
                        step=10.0,
                        unit_of_measurement="W",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_WALL_MASS,
                    default=options.get(CONF_WALL_MASS, "medium"),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=WALL_MASS_OPTIONS,
                        mode=SelectSelectorMode.DROPDOWN,
                        translation_key="wall_mass",
                    )
                ),
                vol.Required(
                    CONF_VENTILATION,
                    default=options.get(CONF_VENTILATION, "high"),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=VENT_OPTIONS,
                        mode=SelectSelectorMode.DROPDOWN,
                        translation_key="ventilation",
                    )
                ),
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=options.get(CONF_UPDATE_INTERVAL, 15),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5,
                        max=120,
                        step=1,
                        unit_of_measurement="min",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
