"""369 HTTP Adapter — Communication with HTTP-based devices and APIs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from core.hal import ActuationResult
from core.models import SensorReading

logger = logging.getLogger("369.hal.http")


class HTTPAdapter:
    """Hardware adapter for HTTP-based sensors and actuators.

    Useful for WiFi-connected ESP32 devices exposing REST endpoints,
    or cloud-based sensor APIs.
    """

    def __init__(self, timeout: float = 10.0):
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def read_sensor(self, sensor_id: str, config: dict) -> SensorReading:
        """Read a sensor value from an HTTP endpoint."""
        url = config.get("url")
        if not url:
            raise ValueError(f"No URL configured for sensor {sensor_id}")

        client = await self._ensure_client()
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

        return SensorReading(
            sensor_id=sensor_id,
            metric=data.get("metric", config.get("type", "unknown")),
            value=float(data["value"]),
            unit=data.get("unit", ""),
            zone=config.get("zone"),
        )

    async def actuate(self, actuator_id: str, command: dict, config: dict) -> ActuationResult:
        """Send a command to an actuator via HTTP POST."""
        url = config.get("url")
        if not url:
            return ActuationResult(
                actuator_id=actuator_id,
                success=False,
                message="No URL configured",
            )

        try:
            client = await self._ensure_client()
            response = await client.post(url, json=command)
            response.raise_for_status()

            return ActuationResult(
                actuator_id=actuator_id,
                success=True,
                message=f"HTTP {response.status_code}",
                data=response.json() if response.headers.get("content-type", "").startswith("application/json") else {},
            )
        except httpx.HTTPError as e:
            return ActuationResult(
                actuator_id=actuator_id,
                success=False,
                message=str(e),
            )

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "adapter": "http",
            "timeout": self._timeout,
        }

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
