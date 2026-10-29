"""Tests for the blueprint auto-copy helper."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.blueprint import models, schemas
from homeassistant.util import yaml as yaml_util

from custom_components.openwindows.blueprint_setup import (
    PACKAGED_BLUEPRINTS,
    copy_blueprints,
)

NOTIF = "openwindows_open_close_notification.yaml"
FAN = "openwindows_fan_control.yaml"
AIRING = "openwindows_airing_notification.yaml"


async def test_copy_blueprints_creates_all_files(hass) -> None:
    """All packaged blueprints land in config/blueprints/automation/openwindows."""
    await hass.async_add_executor_job(copy_blueprints, hass)

    dest = Path(hass.config.path("blueprints", "automation", "openwindows"))
    assert (dest / NOTIF).is_file()
    assert (dest / FAN).is_file()
    assert (dest / AIRING).is_file()


async def test_copy_blueprints_overwrites_existing(hass) -> None:
    """A stale blueprint file is overwritten by the packaged version."""
    dest = Path(hass.config.path("blueprints", "automation", "openwindows"))
    dest.mkdir(parents=True, exist_ok=True)
    stale = dest / FAN
    stale.write_text("stale: content", encoding="utf-8")

    await hass.async_add_executor_job(copy_blueprints, hass)

    assert stale.read_text(encoding="utf-8") != "stale: content"
    assert "fan.turn_on" in stale.read_text(encoding="utf-8")


def test_airing_blueprint_parses() -> None:
    """The airing blueprint loads with HA's blueprint model and has its inputs."""
    path = PACKAGED_BLUEPRINTS / AIRING
    data = yaml_util.load_yaml(str(path))
    blueprint = models.Blueprint(
        data,
        path=str(path),
        expected_domain="automation",
        schema=schemas.BLUEPRINT_SCHEMA,
    )

    assert blueprint.domain == "automation"
    assert set(blueprint.inputs) == {"airing_event", "notify_target"}
    assert data["trigger"][0]["platform"] == "state"
    assert data["action"][-1]["data"]["tag"] == "openwindows_airing"
    # Attribute-only changes (rename, icon) must not re-send the last reminder.
    conditions = [c["value_template"] for c in data["condition"]]
    assert any(
        "trigger.from_state.state != trigger.to_state.state" in c for c in conditions
    )
