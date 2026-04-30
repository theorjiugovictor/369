"""369 Irrigation Agent — Smart watering based on soil and weather data."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from core.agent import Agent369
from core.bulletin import BulletinBoard
from core.hal import HAL
from core.models import Trace, TraceDomain, TraceType

logger = logging.getLogger("369.agent.irrigation")


class IrrigationAgent(Agent369):
    """Controls irrigation based on soil moisture levels and weather forecasts.

    Reads soil agent observations and weather traces to make intelligent
    watering decisions. Actuates solenoid valves through HAL.
    """

    def __init__(self, agent_id: str = "irrigation-agent", config: dict[str, Any] | None = None):
        super().__init__(agent_id=agent_id, domain=TraceDomain.WATER, config=config)
        self.zones = config.get("zones", []) if config else []
        self._min_moisture = 30.0
        self._target_moisture = 50.0
        self._rain_threshold_mm = 5.0  # Skip if >5mm rain expected

    @property
    def capabilities(self) -> list[str]:
        return ["irrigation.schedule", "irrigation.actuate", "water.conservation"]

    async def observe(self, bulletin: BulletinBoard) -> list[Trace]:
        """Gather soil moisture data and weather forecasts."""
        observations = []

        # Read soil conditions
        soil_traces = await bulletin.read_traces(
            domain=TraceDomain.SOIL,
            trace_type=TraceType.OBSERVATION,
            limit=50,
        )
        observations.extend(soil_traces)

        # Read soil alerts (urgent irrigation requests)
        soil_alerts = await bulletin.read_traces(
            domain=TraceDomain.SOIL,
            trace_type=TraceType.ALERT,
            limit=10,
        )
        observations.extend(soil_alerts)

        # Read weather forecasts
        weather_traces = await bulletin.read_traces(
            domain=TraceDomain.WEATHER,
            trace_type=TraceType.OBSERVATION,
            limit=5,
        )
        observations.extend(weather_traces)

        return observations

    async def decide(self, observations: list[Trace]) -> dict:
        """Determine watering plan based on soil and weather data."""
        plan = {"action": "none", "zones_to_water": {}, "skip_reason": None}

        # Check weather — skip if rain expected
        rain_expected = 0.0
        for obs in observations:
            if obs.domain == TraceDomain.WEATHER:
                rain_expected = max(rain_expected, obs.payload.get("precipitation_mm", 0))

        if rain_expected > self._rain_threshold_mm:
            plan["action"] = "skip"
            plan["skip_reason"] = f"Rain expected: {rain_expected}mm"
            return plan

        # Analyze soil moisture per zone
        zone_moisture: dict[str, list[float]] = {}
        urgent_zones: set[str] = set()

        for obs in observations:
            zone = obs.payload.get("zone") or obs.location
            if not zone or zone not in self.zones:
                continue

            if obs.domain == TraceDomain.SOIL:
                if obs.type == TraceType.ALERT and "urgent_irrigation" in obs.payload.get("alert", ""):
                    urgent_zones.add(zone)

                if obs.payload.get("metric") == "soil.moisture":
                    zone_moisture.setdefault(zone, []).append(obs.payload.get("value", 0))

        # Determine watering needs
        for zone_id in self.zones:
            readings = zone_moisture.get(zone_id, [])
            if not readings:
                continue

            avg_moisture = sum(readings) / len(readings)

            if zone_id in urgent_zones or avg_moisture < self._min_moisture:
                duration = int((self._target_moisture - avg_moisture) * 2)  # rough: 2 min per % deficit
                duration = max(5, min(duration, 30))  # clamp 5-30 minutes
                plan["zones_to_water"][zone_id] = {
                    "duration_minutes": duration,
                    "current_moisture": round(avg_moisture, 1),
                    "urgent": zone_id in urgent_zones,
                }
                plan["action"] = "water"

        return plan

    async def act(self, plan: dict, hal: HAL) -> list[Trace]:
        """Open valves for zones that need water."""
        traces = []

        if plan["action"] == "skip":
            traces.append(
                self.make_trace(
                    TraceType.ACTION,
                    {"action": "irrigation_skipped", "reason": plan["skip_reason"]},
                    confidence=0.9,
                )
            )
            return traces

        for zone_id, water_plan in plan.get("zones_to_water", {}).items():
            valve_id = f"valve-{zone_id.split('-')[0]}-1"  # convention: valve-{zone_prefix}-1

            result = await hal.actuate(valve_id, {
                "action": "on",
                "duration_minutes": water_plan["duration_minutes"],
            })

            traces.append(
                self.make_trace(
                    TraceType.ACTION,
                    {
                        "action": "irrigation_started",
                        "zone": zone_id,
                        "valve": valve_id,
                        "duration_minutes": water_plan["duration_minutes"],
                        "current_moisture": water_plan["current_moisture"],
                        "actuator_success": result.success,
                        "urgent": water_plan["urgent"],
                    },
                    location=zone_id,
                    confidence=0.9 if result.success else 0.3,
                    ttl=water_plan["duration_minutes"] * 60,
                )
            )

        return traces

    async def reflect(self, action_traces: list[Trace]) -> list[Trace]:
        """Summarize irrigation actions."""
        if not action_traces:
            return []

        total_minutes = sum(
            t.payload.get("duration_minutes", 0)
            for t in action_traces
            if t.payload.get("action") == "irrigation_started"
        )
        zones_watered = [
            t.location for t in action_traces
            if t.payload.get("action") == "irrigation_started" and t.location
        ]

        return [
            self.make_trace(
                TraceType.OBSERVATION,
                {
                    "summary": "irrigation_cycle_complete",
                    "zones_watered": zones_watered,
                    "total_duration_minutes": total_minutes,
                    "actions_count": len(action_traces),
                },
                confidence=1.0,
            )
        ]
