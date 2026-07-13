"""The OpenWindows integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .blueprint_setup import copy_blueprints
from .config_flow import update_listener
from .const import DOMAIN, PLATFORMS
from .coordinator import OpenWindowsCoordinator

__all__ = ["async_setup_entry", "async_unload_entry", "update_listener"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenWindows from a config entry."""
    coordinator = OpenWindowsCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    coordinator.async_setup_forecast_triggers()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.async_add_executor_job(copy_blueprints, hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
