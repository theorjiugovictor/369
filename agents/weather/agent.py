"""369 Weather Agent — Fetches forecasts from Open-Meteo (free, no key)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from core.agent import Agent369
from core.bulletin import BulletinBoard
from core.hal import HAL
from core.models import Trace, TraceDomain, TraceType

logger = logging.getLogger("369.agent.weather")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherAgent(Agent369):
    """Fetches weather forecasts and writes them as traces for other agents.

    Uses the free Open-Meteo API — no API key required.
    Other agents (especially irrigation) consume weather traces
    to make informed decisions.
    """

    def __init__(self, agent_id: str = "weather-agent", config: dict[str, Any] | None = None):
        super().__init__(agent_id=agent_id, domain=TraceDomain.WEATHER, config=config)
        self._latitude = config.get("latitude", 37.7749) if config else 37.7749
        self._longitude = config.get("longitude", -122.4194) if config else -122.4194
        self._http_client: httpx.AsyncClient | None = None

    @property
    def capabilities(self) -> list[str]:
        return ["weather.forecast", "weather.current", "weather.alerts"]

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=15.0)
        return self._http_client

    async def _fetch_forecast(self) -> dict | None:
        """Fetch weather data from Open-Meteo API."""
        params = {
            "latitude": self._latitude,
            "longitude": self._longitude,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max",
            "timezone": "auto",
            "forecast_days": 3,
        }

        try:
            client = await self._get_client()
            response = await client.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            return response.json()
        except Exception:
            logger.exception("Failed to fetch weather forecast")
            return None

    async def observe(self, bulletin: BulletinBoard) -> list[Trace]:
        """Fetch weather data — this agent's observations come from an external API."""
        data = await self._fetch_forecast()
        if not data:
            return []

        observations = []

        # Current conditions
        current = data.get("current", {})
        if current:
            observations.append(
                self.make_trace(
                    TraceType.OBSERVATION,
                    {
                        "type": "current_weather",
                        "temperature_c": current.get("temperature_2m"),
                        "humidity_pct": current.get("relative_humidity_2m"),
                        "precipitation_mm": current.get("precipitation", 0),
                        "wind_speed_kmh": current.get("wind_speed_10m"),
                        "weather_code": current.get("weather_code"),
                    },
                    confidence=0.95,
                )
            )

        # Daily forecasts
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        for i, date_str in enumerate(dates):
            precip_sum = (daily.get("precipitation_sum") or [0])[i] if i < len(daily.get("precipitation_sum", [])) else 0
            precip_prob = (daily.get("precipitation_probability_max") or [0])[i] if i < len(daily.get("precipitation_probability_max", [])) else 0

            observations.append(
                self.make_trace(
                    TraceType.OBSERVATION,
                    {
                        "type": "daily_forecast",
                        "date": date_str,
                        "temp_max_c": (daily.get("temperature_2m_max") or [None])[i],
                        "temp_min_c": (daily.get("temperature_2m_min") or [None])[i],
                        "precipitation_mm": precip_sum,
                        "precipitation_probability_pct": precip_prob,
                        "wind_max_kmh": (daily.get("wind_speed_10m_max") or [None])[i],
                    },
                    confidence=0.8 if i == 0 else 0.6,
                    ttl=86400,
                )
            )

        return observations

    async def decide(self, observations: list[Trace]) -> dict:
        """Analyze weather for alerts (frost, extreme heat, heavy rain)."""
        plan = {"action": "publish", "alerts": [], "forecasts": observations}

        for obs in observations:
            payload = obs.payload

            # Frost alert
            temp = payload.get("temperature_c") or payload.get("temp_min_c")
            if temp is not None and temp <= 2.0:
                plan["alerts"].append({
                    "type": "frost_warning",
                    "temperature": temp,
                    "date": payload.get("date", "today"),
                })

            # Heavy rain alert
            precip = payload.get("precipitation_mm", 0)
            if precip and precip > 20:
                plan["alerts"].append({
                    "type": "heavy_rain_warning",
                    "precipitation_mm": precip,
                    "date": payload.get("date", "today"),
                })

            # Extreme heat
            temp_max = payload.get("temp_max_c")
            if temp_max is not None and temp_max > 38:
                plan["alerts"].append({
                    "type": "extreme_heat_warning",
                    "temperature": temp_max,
                    "date": payload.get("date", "today"),
                })

        return plan

    async def act(self, plan: dict, hal: HAL) -> list[Trace]:
        """Publish weather alerts as traces."""
        traces = []

        for alert in plan.get("alerts", []):
            traces.append(
                self.make_trace(
                    TraceType.ALERT,
                    alert,
                    confidence=0.85,
                    ttl=43200,
                )
            )

        return traces

    async def reflect(self, action_traces: list[Trace]) -> list[Trace]:
        if not action_traces:
            return []

        return [
            self.make_trace(
                TraceType.OBSERVATION,
                {
                    "summary": "weather_cycle_complete",
                    "alerts_issued": len(action_traces),
                },
            )
        ]
