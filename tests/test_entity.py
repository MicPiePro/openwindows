"""Tests for the OpenWindows base entity."""
from unittest.mock import MagicMock

from custom_components.openwindows.entity import (
    OpenWindowsBaseEntity,
    OpenWindowsDeviceEntity,
)


def test_base_entity_unique_id_and_device_info():
    coordinator = MagicMock()
    entry = MagicMock()
    entry.entry_id = "abc123"

    entity = OpenWindowsBaseEntity(coordinator, entry, "verdict")

    assert entity._attr_has_entity_name is True
    assert entity._attr_unique_id == "abc123_verdict"

    device_info = entity._attr_device_info
    assert device_info["identifiers"] == {("openwindows", "abc123")}
    assert device_info["name"] == "OpenWindows"
    assert device_info["manufacturer"] == "OpenWindows"
    assert entity.coordinator is coordinator


def test_base_entity_key_is_used_verbatim():
    coordinator = MagicMock()
    entry = MagicMock()
    entry.entry_id = "e1"

    entity = OpenWindowsBaseEntity(coordinator, entry, "next_open")

    assert entity._attr_unique_id == "e1_next_open"


def test_device_entity_shares_scheme_with_base_entity():
    coordinator = MagicMock()
    entry = MagicMock()
    entry.entry_id = "abc123"

    base = OpenWindowsBaseEntity(coordinator, entry, "verdict")
    entity = OpenWindowsDeviceEntity(entry, "next_airing")

    assert entity._attr_has_entity_name is True
    assert entity._attr_should_poll is False
    assert entity._attr_unique_id == "abc123_next_airing"
    assert entity._attr_device_info == base._attr_device_info
    assert entity.available is True
