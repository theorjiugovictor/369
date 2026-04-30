"""369 Soil Agent — Monitors soil health and recommends amendments."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from core.agent import Agent369
from core.bulletin import BulletinBoard
from core.hal import HAL
from core.models import Trace, TraceDomain, TraceType

logger = logging.getLogger("369.agent.soil")


class SoilAgent(Agent369):
    """Monitors soil moisture, temperature, and pH across assigned zones.

    Decides on fertilization schedules and writes recommendations
    for other agents (especially irrigation) to consume.
    """

    def __init__(self, agent_id: str = "soil-agent", config: dict[str, Any] | None = None):
        super().__init__(agent_id=agent_id, domain=TraceDomain.SOIL, config=config)
        self.zones = config.get("zones", []) if config else []
        self._moisture_thresholds = {
            "critical_low": 20.0,
            "low": 30.0,
            "optimal_low": 40.0,
            "optimal_high": 60.0,
            "high": 75.0,
        }
        self._temp_thresholds = {
            "too_cold": 5.0,
            "cold": 10.0,
            "optimal_low": 15.0,
            "optimal_high": 27.0,
            "hot": 35.0,
        }

    @property
    def capabilities(self) -> list[str]:
        return ["soil.moisture.monitor", "soil.temperature.monitor", "soil.fertility.recommend"]

    async def observe(self, bulletin: BulletinBoard) -> list[Trace]:
        """Read current soil conditions from sensors via bulletin board."""
        observations = []

        for zone_id in self.zones:
            readings = await bulletin.read_zone(zone_id, "soil.moisture")
            for reading in readings:
                observations.append(
                    self.make_trace(
                        TraceType.OBSERVATION,
                        {
                            "metric": reading.metric,
                            "value": reading.value,
                            "unit": reading.unit,
                            "zone": zone_id,
                            "sensor_id": reading.sensor_id,
                        },
                        location=zone_id,
                    )
                )

            temp_readings = await bulletin.read_zone(zone_id, "soil.temperature")
            for reading in temp_readings:
                observations.append(
                    self.make_trace(
                        TraceType.OBSERVATION,
                        {
                            "metric": reading.metric,
                            "value": reading.value,
                            "unit": reading.unit,
                            "zone": zone_id,
                            "sensor_id": reading.sensor_id,
                        },
                        location=zone_id,
                    )
                )

        return observations

    async def decide(self, observations: list[Trace]) -> dict:
        """Analyze soil conditions and produce a plan."""
        plan = {"action": "monitor", "zones": {}, "alerts": []}

        for obs in observations:
            zone = obs.payload.get("zone", "unknown")
            metric = obs.payload.get("metric", "")
            value = obs.payload.get("value", 0)

            if zone not in plan["zones"]:
                plan["zones"][zone] = {"moisture": None, "temperature": None, "needs": []}

            if "moisture" in metric:
                plan["zones"][zone]["moisture"] = value
                if value < self._moisture_thresholds["critical_low"]:
                    plan["zones"][zone]["needs"].append("urgent_irrigation")
                    plan["alerts"].append(f"CRITICAL: {zone} moisture at {value}%")
                    plan["action"] = "alert"
                elif value < self._moisture_thresholds["low"]:
                    plan["zones"][zone]["needs"].append("irrigation")
                    plan["action"] = "recommend"
                elif value > self._moisture_thresholds["high"]:
                    plan["zones"][zone]["needs"].append("reduce_watering")
                    plan["action"] = "recommend"

            elif "temperature" in metric:
                plan["zones"][zone]["temperature"] = value
                if value < self._temp_thresholds["too_cold"]:
                    plan["zones"][zone]["needs"].append("mulching")
                    plan["alerts"].append(f"WARNING: {zone} soil temp at {value}°C — frost risk")
                    plan["action"] = "alert"
                elif value > self._temp_thresholds["hot"]:
                    plan["zones"][zone]["needs"].append("shading")

        return plan

    async def act(self, plan: dict, hal: HAL) -> list[Trace]:
        """Write recommendations and alerts based on soil analysis."""
        traces = []

        for zone_id, zone_data in plan.get("zones", {}).items():
            for need in zone_data.get("needs", []):
                if need == "urgent_irrigation":
                    traces.append(
                        self.make_trace(
                            TraceType.ALERT,
                            {
                                "alert": "urgent_irrigation_needed",
                                "zone": zone_id,
                                "moisture": zone_data["moisture"],
                                "priority": "high",
                            },
                            location=zone_id,
                            confidence=0.95,
                            ttl=1800,
                        )
                    )
                elif need in ("irrigation", "reduce_watering"):
                    traces.append(
                        self.make_trace(
                            TraceType.RECOMMENDATION,
                            {
                                "recommendation": need,
                                "zone": zone_id,
                                "moisture": zone_data["moisture"],
                                "reason": f"Soil moisture {'below' if need == 'irrigation' else 'above'} optimal range",
                            },
                            location=zone_id,
                            confidence=0.85,
                            ttl=3600,
                        )
                    )
                elif need in ("mulching", "shading"):
                    traces.append(
                        self.make_trace(
                            TraceType.RECOMMENDATION,
                            {
                                "recommendation": need,
                                "zone": zone_id,
                                "temperature": zone_data["temperature"],
                                "reason": f"Soil temperature outside optimal range",
                            },
                            location=zone_id,
                            confidence=0.8,
                        )
                    )

        return traces

    async def reflect(self, action_traces: list[Trace]) -> list[Trace]:
        """Review actions and generate summary trace."""
        if not action_traces:
            return []

        alert_count = sum(1 for t in action_traces if t.type == TraceType.ALERT)
        rec_count = sum(1 for t in action_traces if t.type == TraceType.RECOMMENDATION)
        zones_affected = {t.location for t in action_traces if t.location}

        return [
            self.make_trace(
                TraceType.OBSERVATION,
                {
                    "summary": "soil_cycle_complete",
                    "alerts_issued": alert_count,
                    "recommendations_issued": rec_count,
                    "zones_assessed": list(zones_affected),
                },
                confidence=1.0,
            )
        ]
