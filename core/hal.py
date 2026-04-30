"""369 Hardware Abstraction Layer — Unified interface to physical devices."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from core.models import SensorReading

logger = logging.getLogger("369.hal")


@dataclass
class ActuationResult:
    actuator_id: str
    success: bool
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class HardwareAdapter(Protocol):
    """Protocol for hardware communication adapters."""

    async def read_sensor(self, sensor_id: str, config: dict) -> SensorReading: ...
    async def actuate(self, actuator_id: str, command: dict, config: dict) -> ActuationResult: ...
    async def health_check(self) -> dict[str, Any]: ...


class HAL:
    """Hardware Abstraction Layer.

    Routes sensor reads and actuator commands to the correct adapter
    based on device registry configuration.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, HardwareAdapter] = {}
        self._devices: dict[str, dict[str, Any]] = {}

    def register_adapter(self, name: str, adapter: HardwareAdapter) -> None:
        """Register a hardware communication adapter."""
        self._adapters[name] = adapter
        logger.info("Registered HAL adapter: %s", name)

    def register_device(self, device_config: dict[str, Any]) -> str:
        """Register a device (sensor or actuator) and return its ID."""
        device_id = device_config["id"]
        self._devices[device_id] = device_config
        logger.debug("Registered device: %s (adapter: %s)", device_id, device_config.get("adapter"))
        return device_id

    async def read_sensor(self, sensor_id: str) -> SensorReading:
        """Read a sensor value through the appropriate adapter."""
        device = self._devices.get(sensor_id)
        if not device:
            raise KeyError(f"Unknown sensor: {sensor_id}")

        adapter_name = device.get("adapter", "mock")
        adapter = self._adapters.get(adapter_name)
        if not adapter:
            raise KeyError(f"No adapter registered: {adapter_name}")

        return await adapter.read_sensor(sensor_id, device)

    async def read_zone(self, zone: str, metric: str | None = None) -> list[SensorReading]:
        """Read all sensors in a zone, optionally filtered by metric type."""
        readings = []
        for device_id, config in self._devices.items():
            if config.get("zone") == zone or config.get("type", "").startswith(metric or ""):
                try:
                    reading = await self.read_sensor(device_id)
                    if metric is None or reading.metric == metric:
                        readings.append(reading)
                except Exception:
                    logger.warning("Failed to read sensor %s", device_id)
        return readings

    async def actuate(self, actuator_id: str, command: dict[str, Any]) -> ActuationResult:
        """Send a command to an actuator through the appropriate adapter."""
        device = self._devices.get(actuator_id)
        if not device:
            return ActuationResult(actuator_id=actuator_id, success=False, message="Unknown actuator")

        adapter_name = device.get("adapter", "mock")
        adapter = self._adapters.get(adapter_name)
        if not adapter:
            return ActuationResult(actuator_id=actuator_id, success=False, message=f"No adapter: {adapter_name}")

        return await adapter.actuate(actuator_id, command, device)

    async def health_check(self) -> dict[str, Any]:
        """Check health of all registered adapters."""
        results = {}
        for name, adapter in self._adapters.items():
            try:
                results[name] = await adapter.health_check()
            except Exception as e:
                results[name] = {"status": "error", "message": str(e)}
        return {"adapters": results, "devices": len(self._devices)}
