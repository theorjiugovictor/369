"""369 Soil Rules — Domain knowledge for soil health assessment."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SoilThresholds:
    """Optimal ranges for soil metrics by zone type."""

    moisture_min: float = 30.0
    moisture_max: float = 65.0
    moisture_critical_low: float = 20.0
    temp_min: float = 10.0
    temp_max: float = 30.0
    ph_min: float = 6.0
    ph_max: float = 7.5


ZONE_TYPE_THRESHOLDS: dict[str, SoilThresholds] = {
    "growing": SoilThresholds(moisture_min=35.0, moisture_max=60.0),
    "orchard": SoilThresholds(moisture_min=25.0, moisture_max=55.0),
    "lawn": SoilThresholds(moisture_min=30.0, moisture_max=50.0),
    "controlled": SoilThresholds(moisture_min=40.0, moisture_max=65.0, temp_min=15.0, temp_max=28.0),
}


def get_thresholds(zone_type: str) -> SoilThresholds:
    """Get soil thresholds for a specific zone type."""
    return ZONE_TYPE_THRESHOLDS.get(zone_type, SoilThresholds())


def assess_moisture(value: float, zone_type: str = "growing") -> str:
    """Assess soil moisture level. Returns: critical_low, low, optimal, high, critical_high."""
    thresholds = get_thresholds(zone_type)
    if value < thresholds.moisture_critical_low:
        return "critical_low"
    if value < thresholds.moisture_min:
        return "low"
    if value <= thresholds.moisture_max:
        return "optimal"
    if value <= thresholds.moisture_max + 15:
        return "high"
    return "critical_high"


def assess_temperature(value: float, zone_type: str = "growing") -> str:
    """Assess soil temperature. Returns: frost_risk, cold, optimal, hot, critical_hot."""
    thresholds = get_thresholds(zone_type)
    if value < 2.0:
        return "frost_risk"
    if value < thresholds.temp_min:
        return "cold"
    if value <= thresholds.temp_max:
        return "optimal"
    if value <= thresholds.temp_max + 5:
        return "hot"
    return "critical_hot"


def fertilization_window(soil_temp: float, moisture: float) -> bool:
    """Check if conditions are suitable for fertilizer application."""
    return 12.0 <= soil_temp <= 28.0 and 35.0 <= moisture <= 60.0
