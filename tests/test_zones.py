"""Tests for the pure zones aggregation module."""
from __future__ import annotations

import math

from custom_components.openwindows.engine import ZoneReading
from custom_components.openwindows.zones import aggregate_zone


def test_aggregate_zone_temp_is_max_of_non_none_values():
    r = aggregate_zone("crossvent", [20.0, 22.0, 24.0], [40.0, 50.0, 60.0])
    assert isinstance(r, ZoneReading)
    assert r.name == "crossvent"
    assert r.temp == 24.0


def test_aggregate_zone_humidity_is_mean_of_non_none_values():
    r = aggregate_zone("crossvent", [20.0, 22.0, 24.0], [40.0, 50.0, 60.0])
    assert r.humidity == 50.0


def test_aggregate_zone_ignores_none_entries():
    r = aggregate_zone("crossvent", [20.0, None, 24.0], [None, 50.0, None])
    assert r.temp == 24.0
    assert r.humidity == 50.0


def test_aggregate_zone_empty_lists_give_none():
    r = aggregate_zone("crossvent", [], [])
    assert r.name == "crossvent"
    assert r.temp is None
    assert r.humidity is None


def test_aggregate_zone_all_none_gives_none():
    r = aggregate_zone("crossvent", [None, None], [None])
    assert r.temp is None
    assert r.humidity is None


def test_aggregate_zone_single_value():
    r = aggregate_zone("bureau", [26.5], [45.0])
    assert math.isclose(r.temp, 26.5)
    assert math.isclose(r.humidity, 45.0)


def test_aggregate_zone_hottest_room_wins_over_cooler_rooms():
    # The hottest room among the zone's sensors drives the temperature.
    r = aggregate_zone("crossvent", [21.0, 29.5, 24.0], [50.0, 40.0, 60.0])
    assert r.temp == 29.5
