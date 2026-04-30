"""369 MQTT Adapter — Communication via MQTT broker."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from core.hal import ActuationResult
from core.models import SensorReading

logger = logging.getLogger("369.hal.mqtt")


class MQTTAdapter:
    """Hardware adapter that communicates through MQTT.

    Sensors publish readings to topics; actuators receive commands on topics.
    Uses paho-mqtt under the hood.
    """

    def __init__(self, broker: str = "localhost", port: int = 1883):
        self._broker = broker
        self._port = port
        self._client = None
        self._latest_readings: dict[str, dict] = {}
        self._connected = False

    async def connect(self) -> None:
        """Connect to the MQTT broker."""
        try:
            import paho.mqtt.client as mqtt

            self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            self._client.on_message = self._on_message
            self._client.on_connect = self._on_connect

            self._client.connect_async(self._broker, self._port)
            self._client.loop_start()
            logger.info("MQTT adapter connecting to %s:%d", self._broker, self._port)
        except Exception:
            logger.exception("Failed to connect MQTT adapter")

    def _on_connect(self, client, userdata, flags, rc, properties=None) -> None:
        if rc == 0:
            self._connected = True
            client.subscribe("369/sensors/#")
            logger.info("MQTT adapter connected and subscribed")
        else:
            logger.error("MQTT connection failed with code %d", rc)

    def _on_message(self, client, userdata, msg) -> None:
        try:
            payload = json.loads(msg.payload.decode())
            self._latest_readings[msg.topic] = payload
        except Exception:
            logger.warning("Failed to parse MQTT message on %s", msg.topic)

    async def read_sensor(self, sensor_id: str, config: dict) -> SensorReading:
        """Read the latest value received on a sensor's MQTT topic."""
        topic = config.get("topic", f"369/sensors/{sensor_id}")
        data = self._latest_readings.get(topic)

        if data is None:
            raise ValueError(f"No data received for sensor {sensor_id} on topic {topic}")

        return SensorReading(
            sensor_id=sensor_id,
            metric=data.get("metric", config.get("type", "unknown")),
            value=float(data["value"]),
            unit=data.get("unit", ""),
            zone=config.get("zone"),
        )

    async def actuate(self, actuator_id: str, command: dict, config: dict) -> ActuationResult:
        """Publish a command to an actuator's MQTT topic."""
        if not self._client or not self._connected:
            return ActuationResult(
                actuator_id=actuator_id,
                success=False,
                message="MQTT not connected",
            )

        topic = config.get("topic", f"369/actuators/{actuator_id}")
        payload = json.dumps(command)

        result = self._client.publish(topic, payload, qos=1)
        success = result.rc == 0

        return ActuationResult(
            actuator_id=actuator_id,
            success=success,
            message="Published" if success else f"Publish failed: rc={result.rc}",
        )

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy" if self._connected else "disconnected",
            "adapter": "mqtt",
            "broker": f"{self._broker}:{self._port}",
            "topics_tracked": len(self._latest_readings),
        }

    async def disconnect(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
