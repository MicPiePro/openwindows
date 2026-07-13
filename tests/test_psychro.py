"""Pure-pytest tests for the Magnus-Tetens dew point (no Home Assistant)."""
import pytest

from custom_components.openwindows.psychro import dew_point


def test_dew_point_30c_50pct():
    # Reference value computed from the Magnus formula.
    assert dew_point(30.0, 50.0) == pytest.approx(18.4409, abs=0.001)


def test_dew_point_22c_40pct():
    assert dew_point(22.0, 40.0) == pytest.approx(7.7722, abs=0.001)


def test_dew_point_25c_50pct():
    assert dew_point(25.0, 50.0) == pytest.approx(13.8516, abs=0.001)


def test_dew_point_at_saturation_equals_air_temp():
    # At 100% relative humidity the dew point equals the air temperature.
    assert dew_point(15.0, 100.0) == pytest.approx(15.0, abs=0.001)
    assert dew_point(28.0, 100.0) == pytest.approx(28.0, abs=0.001)


def test_dew_point_monotonic_in_humidity():
    # Wetter air -> higher dew point at fixed temperature.
    assert dew_point(28.0, 30.0) < dew_point(28.0, 60.0) < dew_point(28.0, 90.0)


def test_dew_point_monotonic_in_temperature():
    # Warmer air at fixed RH -> higher dew point.
    assert dew_point(20.0, 50.0) < dew_point(30.0, 50.0)
