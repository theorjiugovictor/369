"""369 Mock Adapter — Simulated hardware for testing and development."""

from __future__ import annotations

import logging
import math
import random
from datetime import datetime, timezone
from typing import Any

from core.hal import ActuationResult
from core.models import SensorReading

logger = logging.getLogger("369.hal.mock")

# Realistic value ranges for different sensor types
SENSOR_PROFILES: dict[str, dict[str, Any]] = {
    "soil_moisture": {
        "metric": "soil.moisture",
        "unit": "%",
        "base": 45.0,
        "amplitude": 20.0,
        "noise": 3.0,
    },
    "soil_temperature": {
        "metric": "soil.temperature",
        "unit": "°C",
        "base": 18.0,
        "amplitude": 8.0,
        "noise": 1.0,
    },
    "temperature": {
        "metric": "temperature",
        "unit": "°C",
        "base": 55.0,  # Compost runs hot
        "amplitude": 15.0,
        "noise": 2.0,
    },
    "moisture": {
        "metric": "moisture",
        "unit": "%",
        "base": 50.0,
        "amplitude": 15.0,
        "noise": 5.0,
    },
    "air_temperature": {
        "metric": "air.temperature",
        "unit": "°C",
        "base": 22.0,
        "amplitude": 10.0,
        "noise": 1.5,
    },
    "humidity": {
        "metric": "air.humidity",
        "unit": "%",
        "base": 60.0,
        "amplitude": 20.0,
        "noise": 5.0,
    },
    "light": {
        "metric": "light.lux",
        "unit": "lux",
        "base": 30000.0,
        "amplitude": 25000.0,
        "noise": 2000.0,
    },
    "ph": {
        "metric": "soil.ph",
        "unit": "pH",
        "base": 6.5,
        "amplitude": 0.5,
        "noise": 0.2,
    },
}


class MockAdapter:
    """Simulated hardware adapter that generates realistic sensor data.

    Uses sinusoidal patterns with noise to simulate diurnal cycles
    and natural variation in environmental measurements.
    """

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
        self._actuator_states: dict[str, dict] = {}
        self._start_time = datetime.now(timezone.utc)
        logger.info("Mock adapter initialized (seed=%d)", seed)

    def _generate_value(self, profile: dict[str, Any]) -> float:
        """Generate a realistic sensor value with diurnal variation and noise."""
        now = datetime.now(timezone.utc)
        elapsed_hours = (now - self._start_time).total_seconds() / 3600.0

        # Sinusoidal diurnal cycle (peaks at ~14:00)
        diurnal = math.sin((elapsed_hours - 6) * math.pi / 12)

        value = (
            profile["base"]
            + profile["amplitude"] * diurnal * 0.5
            + self._rng.gauss(0, profile["noise"])
        )

        # Clamp to reasonable ranges
        if profile["unit"] == "%":
            value = max(0.0, min(100.0, value))
        elif profile["unit"] == "pH":
            value = max(3.0, min(9.0, value))
        elif profile["unit"] == "lux":
            value = max(0.0, value)

        return round(value, 2)

    async def read_sensor(self, sensor_id: str, config: dict) -> SensorReading:
        """Generate a simulated sensor reading."""
        sensor_type = config.get("type", "soil_moisture")
        profile = SENSOR_PROFILES.get(sensor_type, SENSOR_PROFILES["soil_moisture"])

        value = self._generate_value(profile)

        reading = SensorReading(
            sensor_id=sensor_id,
            metric=profile["metric"],
            value=value,
            unit=profile["unit"],
            zone=config.get("zone"),
        )

        logger.debug("Mock read %s: %.2f %s", sensor_id, value, profile["unit"])
        return reading

    async def actuate(self, actuator_id: str, command: dict, config: dict) -> ActuationResult:
        """Simulate actuator command execution."""
        action = command.get("action", "unknown")
        self._actuator_states[actuator_id] = {
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "command": command,
        }

        logger.info("Mock actuate %s: %s", actuator_id, action)

        return ActuationResult(
            actuator_id=actuator_id,
            success=True,
            message=f"Mock {action} executed",
            data={"simulated": True, "state": self._actuator_states[actuator_id]},
        )

    async def health_check(self) -> dict[str, Any]:
        """Return mock adapter health status."""
        return {
            "status": "healthy",
            "adapter": "mock",
            "active_actuators": len(self._actuator_states),
            "uptime_seconds": (datetime.now(timezone.utc) - self._start_time).total_seconds(),
        }
