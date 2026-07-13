"""Tests for the blueprint auto-copy helper."""

from __future__ import annotations

from pathlib import Path

from custom_components.openwindows.blueprint_setup import copy_blueprints

NOTIF = "openwindows_open_close_notification.yaml"
FAN = "openwindows_fan_control.yaml"


async def test_copy_blueprints_creates_both_files(hass) -> None:
    """Both packaged blueprints land in config/blueprints/automation/openwindows."""
    await hass.async_add_executor_job(copy_blueprints, hass)

    dest = Path(hass.config.path("blueprints", "automation", "openwindows"))
    assert (dest / NOTIF).is_file()
    assert (dest / FAN).is_file()


async def test_copy_blueprints_overwrites_existing(hass) -> None:
    """A stale blueprint file is overwritten by the packaged version."""
    dest = Path(hass.config.path("blueprints", "automation", "openwindows"))
    dest.mkdir(parents=True, exist_ok=True)
    stale = dest / FAN
    stale.write_text("stale: content", encoding="utf-8")

    await hass.async_add_executor_job(copy_blueprints, hass)

    assert stale.read_text(encoding="utf-8") != "stale: content"
    assert "fan.turn_on" in stale.read_text(encoding="utf-8")
