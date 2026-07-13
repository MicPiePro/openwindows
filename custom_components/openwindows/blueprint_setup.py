"""Auto-copy of the packaged OpenWindows blueprints into the HA config dir."""

from __future__ import annotations

import shutil
from pathlib import Path

from homeassistant.core import HomeAssistant

# The blueprints are shipped inside the integration package so that a HACS
# install (which only copies custom_components/openwindows/) still ships them.
PACKAGED_BLUEPRINTS: Path = Path(__file__).parent / "blueprints"


def copy_blueprints(hass: HomeAssistant) -> None:
    """Copy packaged blueprints to config/blueprints/automation/openwindows.

    Blocking file I/O: call via ``hass.async_add_executor_job``. Existing files
    are overwritten so integration upgrades ship the latest blueprint versions.
    """
    dest = Path(hass.config.path("blueprints", "automation", "openwindows"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(PACKAGED_BLUEPRINTS, dest, dirs_exist_ok=True)
