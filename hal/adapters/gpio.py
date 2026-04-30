"""369 GPIO Adapter — Direct Raspberry Pi GPIO control."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from core.hal import ActuationResult
from core.models import SensorReading

logger = logging.getLogger("369.hal.gpio")


class GPIOAdapter:
    """Hardware adapter for direct Raspberry Pi GPIO pin control.

    Requires RPi.GPIO package (optional dependency).
    Falls back gracefully if not running on a Pi.
    """

    def __init__(self):
        self._gpio = None
        self._initialized = False
        self._pin_states: dict[int, Any] = {}

        try:
            import RPi.GPIO as GPIO
            self._gpio = GPIO
            self._gpio.setmode(GPIO.BCM)
            self._initialized = True
            logger.info("GPIO adapter initialized (BCM mode)")
        except (ImportError, RuntimeError):
            logger.warning("RPi.GPIO not available — GPIO adapter in stub mode")

    async def read_sensor(self, sensor_id: str, config: dict) -> SensorReading:
        """Read a sensor connected to a GPIO pin."""
        pin = config.get("pin")
        if not self._initialized or pin is None:
            raise RuntimeError(f"GPIO not available for sensor {sensor_id}")

        self._gpio.setup(pin, self._gpio.IN)
        raw_value = self._gpio.input(pin)

        return SensorReading(
            sensor_id=sensor_id,
            metric=config.get("type", "gpio.digital"),
            value=float(raw_value),
            unit="digital",
            zone=config.get("zone"),
        )

    async def actuate(self, actuator_id: str, command: dict, config: dict) -> ActuationResult:
        """Control a GPIO pin (on/off for relays, solenoids, etc.)."""
        pin = config.get("pin")
        if not self._initialized or pin is None:
            return ActuationResult(
                actuator_id=actuator_id,
                success=False,
                message="GPIO not available",
            )

        action = command.get("action", "off")
        self._gpio.setup(pin, self._gpio.OUT)

        if action == "on":
            self._gpio.output(pin, self._gpio.HIGH)
            self._pin_states[pin] = True
        else:
            self._gpio.output(pin, self._gpio.LOW)
            self._pin_states[pin] = False

        return ActuationResult(
            actuator_id=actuator_id,
            success=True,
            message=f"GPIO pin {pin} set to {action}",
            data={"pin": pin, "state": action},
        )

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy" if self._initialized else "unavailable",
            "adapter": "gpio",
            "active_pins": len(self._pin_states),
        }

    def cleanup(self) -> None:
        if self._initialized:
            self._gpio.cleanup()
            logger.info("GPIO cleanup complete")
