"""369 Device Registry — Manages device configuration and discovery."""

from __future__ import annotations

import logging
from typing import Any

from core.config import ActuatorConfig, SensorConfig, ZoneConfig

logger = logging.getLogger("369.hal.registry")


class DeviceRegistry:
    """Central registry of all configured sensors and actuators.

    Provides lookup by ID, zone, type, and adapter for the HAL
    and agent subsystems.
    """

    def __init__(self):
        self._sensors: dict[str, dict[str, Any]] = {}
        self._actuators: dict[str, dict[str, Any]] = {}

    def register_from_zones(self, zones: list[ZoneConfig]) -> None:
        """Bulk-register sensors from zone configurations."""
        for zone in zones:
            for sensor in zone.sensors:
                self._sensors[sensor.id] = {
                    "id": sensor.id,
                    "type": sensor.type,
                    "adapter": sensor.adapter,
                    "topic": sensor.topic,
                    "zone": zone.id,
                }
        logger.info("Registered %d sensors from %d zones", len(self._sensors), len(zones))

    def register_actuators(self, actuators: list[ActuatorConfig]) -> None:
        """Bulk-register actuators."""
        for act in actuators:
            self._actuators[act.id] = {
                "id": act.id,
                "type": act.type,
                "adapter": act.adapter,
                "topic": act.topic,
                "zone": act.zone,
            }
        logger.info("Registered %d actuators", len(self._actuators))

    def get_sensor(self, sensor_id: str) -> dict[str, Any] | None:
        return self._sensors.get(sensor_id)

    def get_actuator(self, actuator_id: str) -> dict[str, Any] | None:
        return self._actuators.get(actuator_id)

    def sensors_for_zone(self, zone_id: str) -> list[dict[str, Any]]:
        return [s for s in self._sensors.values() if s.get("zone") == zone_id]

    def actuators_for_zone(self, zone_id: str) -> list[dict[str, Any]]:
        return [a for a in self._actuators.values() if a.get("zone") == zone_id]

    def all_sensors(self) -> list[dict[str, Any]]:
        return list(self._sensors.values())

    def all_actuators(self) -> list[dict[str, Any]]:
        return list(self._actuators.values())

    @property
    def sensor_count(self) -> int:
        return len(self._sensors)

    @property
    def actuator_count(self) -> int:
        return len(self._actuators)
