"""369 Irrigation Rules — Watering schedule logic."""

from __future__ import annotations

from datetime import datetime


def calculate_water_duration(
    current_moisture: float,
    target_moisture: float = 50.0,
    zone_area_sqft: float = 100.0,
    soil_type: str = "loam",
) -> int:
    """Calculate watering duration in minutes based on moisture deficit."""
    deficit = max(0, target_moisture - current_moisture)

    # Soil infiltration rates (inches/hour)
    infiltration_rates = {
        "sand": 2.0,
        "loam": 1.0,
        "clay": 0.5,
        "silt": 0.75,
    }
    rate = infiltration_rates.get(soil_type, 1.0)

    # Rough estimation: each % moisture deficit needs ~0.5 min per 100 sqft
    minutes = (deficit * 0.5 * (zone_area_sqft / 100)) / rate
    return max(5, min(int(minutes), 60))


def should_skip_for_rain(precipitation_forecast_mm: float, threshold: float = 5.0) -> bool:
    """Determine if irrigation should be skipped due to expected rain."""
    return precipitation_forecast_mm >= threshold


def optimal_watering_window(hour: int) -> bool:
    """Check if current hour is in the optimal watering window (early morning or evening)."""
    return hour < 8 or hour >= 19
