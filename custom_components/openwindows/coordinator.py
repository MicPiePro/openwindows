"""Data update coordinator for the OpenWindows integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
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
    CONF_SOLAR_WEATHER,
    CONF_TEMP_WEATHER,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from .engine import EngineConfig, HourForecast, Snapshot, run_decision_engine
from .psychro import dew_point
from .zones import aggregate_zone

_LOGGER = logging.getLogger(__name__)


class OpenWindowsCoordinator(DataUpdateCoordinator[Snapshot]):
    """Fetch forecasts + sensor state and compute the window-advice Snapshot."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the coordinator from the config entry data + options."""
        self.entry = entry
        self._cfg: dict = {**entry.data, **entry.options}
        interval = int(self._cfg.get(CONF_UPDATE_INTERVAL, 15))
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval),
        )

    def _state_float(self, entity_id: str | None) -> float | None:
        """Return the numeric state of an entity, or None if missing/unavailable."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", ""):
            return None
        try:
            return float(state.state)
        except (ValueError, TypeError):
            return None

    def _read_zone(self, name, temp_ids, hum_ids):
        """Build a ZoneReading (max temp / mean humidity) for a zone."""
        if isinstance(temp_ids, str):
            temp_ids = [temp_ids]
        if isinstance(hum_ids, str):
            hum_ids = [hum_ids]
        temps = [self._state_float(eid) for eid in (temp_ids or [])]
        hums = [self._state_float(eid) for eid in (hum_ids or [])]
        return aggregate_zone(name, temps, hums)

    def _parse_forecasts(self, temp_fc: list, solar_fc: list) -> list[HourForecast]:
        """Merge the temp-source and solar-source hourly forecasts into HourForecasts.

        The temperature weather source drives time/temp/humidity (and dew point when
        both are present). Cloud cover and solar are pulled from the solar weather
        source, aligned by index.
        """
        hours: list[HourForecast] = []
        for i, item in enumerate(temp_fc):
            raw_time = item.get("datetime")
            time = dt_util.parse_datetime(raw_time) if raw_time else None
            if time is None:
                continue
            temp = item.get("temperature")
            humidity = item.get("humidity")
            dp = (
                dew_point(temp, humidity)
                if temp is not None and humidity is not None
                else None
            )
            cloud = None
            solar = None
            if i < len(solar_fc):
                source = solar_fc[i]
                cloud = source.get("cloud_coverage")
                solar = source.get("solar")
            hours.append(
                HourForecast(
                    time=time,
                    temp=temp,
                    humidity=humidity,
                    dew_point=dp,
                    cloud_cover=cloud,
                    solar=solar,
                )
            )
        return hours

    async def _async_get_forecast(self, entity_id: str) -> list:
        """Call weather.get_forecasts (hourly) for one entity and return its list."""
        response = await self.hass.services.async_call(
            "weather",
            "get_forecasts",
            {"type": "hourly", "entity_id": entity_id},
            blocking=True,
            return_response=True,
        )
        if not response or entity_id not in response:
            return []
        return response[entity_id].get("forecast", [])

    async def _async_update_data(self) -> Snapshot:
        """Fetch data, run the decision engine, and return a Snapshot."""
        temp_entity = self._cfg.get(CONF_TEMP_WEATHER)
        solar_entity = self._cfg.get(CONF_SOLAR_WEATHER)
        if not temp_entity:
            raise UpdateFailed("No temperature weather entity configured")

        temp_fc = await self._async_get_forecast(temp_entity)
        solar_fc = (
            await self._async_get_forecast(solar_entity) if solar_entity else []
        )

        if not temp_fc:
            raise UpdateFailed(f"No hourly forecast available for {temp_entity}")

        forecasts = self._parse_forecasts(temp_fc, solar_fc)
        if not forecasts:
            raise UpdateFailed("Hourly forecast could not be parsed")

        crossvent = self._read_zone(
            "crossvent",
            self._cfg.get(CONF_CROSSVENT_TEMP),
            self._cfg.get(CONF_CROSSVENT_HUM),
        )
        bureau = self._read_zone(
            "bureau",
            self._cfg.get(CONF_BUREAU_TEMP),
            self._cfg.get(CONF_BUREAU_HUM),
        )

        door_entity = self._cfg.get(CONF_DOOR)
        door_state = self.hass.states.get(door_entity) if door_entity else None
        door_open = door_state is not None and door_state.state == "on"

        cfg = EngineConfig(
            comfort_target=float(self._cfg.get(CONF_COMFORT_TARGET, 25.0)),
            open_margin=float(self._cfg.get(CONF_OPEN_MARGIN, 2.0)),
            close_margin=float(self._cfg.get(CONF_CLOSE_MARGIN, 0.3)),
            min_indoor=float(self._cfg.get(CONF_MIN_INDOOR, 23.0)),
            humidity_gate_enabled=bool(self._cfg.get(CONF_HUMIDITY_GATE, True)),
            max_outdoor_dewpoint=float(self._cfg.get(CONF_MAX_DEWPOINT, 18.0)),
        )

        try:
            snapshot = await self.hass.async_add_executor_job(
                run_decision_engine,
                dt_util.utcnow(),
                forecasts,
                crossvent,
                bureau,
                door_open,
                cfg,
            )
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Decision engine failed: {err}") from err

        return snapshot

    @callback
    def async_setup_forecast_triggers(self) -> None:
        """Refresh whenever either weather entity publishes a new state.

        The unsubscribe callback is registered on the config entry so it is torn
        down automatically on unload.
        """
        entities = [
            entity_id
            for entity_id in (
                self._cfg.get(CONF_TEMP_WEATHER),
                self._cfg.get(CONF_SOLAR_WEATHER),
            )
            if entity_id
        ]
        if not entities:
            return

        @callback
        def _handle_weather_event(event) -> None:
            self.hass.async_create_task(self.async_request_refresh())

        unsub = async_track_state_change_event(
            self.hass, entities, _handle_weather_event
        )
        self.entry.async_on_unload(unsub)
