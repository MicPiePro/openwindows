"""Pure psychrometric helpers for OpenWindows V1 (no numpy, no Home Assistant)."""
from __future__ import annotations

import math


def dew_point(temp_c: float, rh_pct: float) -> float:
    """Return the dew point in degrees Celsius (Magnus-Tetens approximation).

    gamma = ln(rh/100) + 17.62 * t / (243.12 + t)
    dew   = 243.12 * gamma / (17.62 - gamma)
    """
    gamma = math.log(rh_pct / 100.0) + (17.62 * temp_c) / (243.12 + temp_c)
    return (243.12 * gamma) / (17.62 - gamma)
