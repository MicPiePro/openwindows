"""Tests for the pure zones aggregation module."""
from __future__ import annotations

import math

from custom_components.openwindows.engine import ZoneReading
from custom_components.openwindows.zones import mean_reading, select_reference


def test_mean_reading_averages_non_none_values():
    r = mean_reading("crossvent", [20.0, 22.0, 24.0], [40.0, 50.0, 60.0])
    assert isinstance(r, ZoneReading)
    assert r.name == "crossvent"
    assert r.temp == 22.0
    assert r.humidity == 50.0


def test_mean_reading_ignores_none_entries():
    r = mean_reading("crossvent", [20.0, None, 24.0], [None, 50.0, None])
    assert r.temp == 22.0
    assert r.humidity == 50.0


def test_mean_reading_empty_lists_give_none():
    r = mean_reading("bedrooms", [], [])
    assert r.name == "bedrooms"
    assert r.temp is None
    assert r.humidity is None


def test_mean_reading_all_none_gives_none():
    r = mean_reading("bedrooms", [None, None], [None])
    assert r.temp is None
    assert r.humidity is None


def test_mean_reading_single_value():
    r = mean_reading("bureau", [26.5], [45.0])
    assert math.isclose(r.temp, 26.5)
    assert math.isclose(r.humidity, 45.0)


def test_select_reference_ac_on_with_bedroom_temp_picks_bedrooms():
    crossvent = ZoneReading("crossvent", 24.0, 50.0)
    bedrooms = ZoneReading("bedrooms", 26.0, 55.0)
    reading, label = select_reference(crossvent, bedrooms, ac_on=True)
    assert label == "bedrooms"
    assert reading is bedrooms


def test_select_reference_ac_off_picks_crossvent():
    crossvent = ZoneReading("crossvent", 24.0, 50.0)
    bedrooms = ZoneReading("bedrooms", 26.0, 55.0)
    reading, label = select_reference(crossvent, bedrooms, ac_on=False)
    assert label == "crossvent"
    assert reading is crossvent


def test_select_reference_ac_on_but_bedroom_temp_none_falls_back_to_crossvent():
    crossvent = ZoneReading("crossvent", 24.0, 50.0)
    bedrooms = ZoneReading("bedrooms", None, 55.0)
    reading, label = select_reference(crossvent, bedrooms, ac_on=True)
    assert label == "crossvent"
    assert reading is crossvent


def test_select_reference_ac_off_with_bedroom_temp_still_crossvent():
    crossvent = ZoneReading("crossvent", None, None)
    bedrooms = ZoneReading("bedrooms", 26.0, 55.0)
    reading, label = select_reference(crossvent, bedrooms, ac_on=False)
    assert label == "crossvent"
    assert reading is crossvent
