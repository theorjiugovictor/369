"""369 Compost Agent — Monitors compost maturity and recommends actions."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from core.agent import Agent369
from core.bulletin import BulletinBoard
from core.hal import HAL
from core.models import Trace, TraceDomain, TraceType

logger = logging.getLogger("369.agent.compost")


class CompostAgent(Agent369):
    """Tracks compost bin temperature and moisture to estimate maturity.

    Uses temperature curve analysis to determine composting phase
    and recommends turning or material inputs.
    """

    # Composting phases by temperature
    PHASES = {
        "mesophilic_start": (20, 40),   # Initial heating
        "thermophilic": (40, 70),        # Active decomposition
        "mesophilic_end": (25, 40),      # Cooling
        "maturation": (15, 25),          # Curing
    }

    def __init__(self, agent_id: str = "compost-agent", config: dict[str, Any] | None = None):
        super().__init__(agent_id=agent_id, domain=TraceDomain.COMPOST, config=config)
        self.zones = config.get("zones", []) if config else []

    @property
    def capabilities(self) -> list[str]:
        return ["compost.temperature.monitor", "compost.maturity.estimate", "compost.action.recommend"]

    async def observe(self, bulletin: BulletinBoard) -> list[Trace]:
        """Read compost bin sensor data."""
        observations = []

        for zone_id in self.zones:
            temp_readings = await bulletin.read_zone(zone_id, "temperature")
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

            moisture_readings = await bulletin.read_zone(zone_id, "moisture")
            for reading in moisture_readings:
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

    def _determine_phase(self, temperature: float) -> str:
        """Determine composting phase based on current temperature."""
        if temperature >= 40:
            return "thermophilic"
        if temperature >= 25:
            return "mesophilic"
        if temperature >= 15:
            return "maturation"
        return "cold"

    def _estimate_maturity_pct(self, temperature: float, moisture: float) -> float:
        """Rough maturity estimate. Real implementation would track over time."""
        phase = self._determine_phase(temperature)
        base = {"cold": 0.0, "maturation": 70.0, "mesophilic": 30.0, "thermophilic": 50.0}
        maturity = base.get(phase, 0.0)

        # Moisture penalty — too dry or too wet slows composting
        if moisture < 40 or moisture > 70:
            maturity *= 0.8

        return min(100.0, maturity)

    async def decide(self, observations: list[Trace]) -> dict:
        """Analyze compost conditions and determine actions."""
        plan = {"action": "monitor", "bins": {}}

        for obs in observations:
            zone = obs.payload.get("zone", "unknown")
            if zone not in plan["bins"]:
                plan["bins"][zone] = {"temperature": None, "moisture": None, "needs": []}

            metric = obs.payload.get("metric", "")
            value = obs.payload.get("value", 0)

            if "temperature" in metric:
                plan["bins"][zone]["temperature"] = value
                phase = self._determine_phase(value)
                plan["bins"][zone]["phase"] = phase

                if value > 65:
                    plan["bins"][zone]["needs"].append("turn_immediately")
                    plan["action"] = "recommend"
                elif value < 25 and phase != "maturation":
                    plan["bins"][zone]["needs"].append("add_greens")
                    plan["action"] = "recommend"

            elif "moisture" in metric:
                plan["bins"][zone]["moisture"] = value
                if value < 40:
                    plan["bins"][zone]["needs"].append("add_water")
                    plan["action"] = "recommend"
                elif value > 70:
                    plan["bins"][zone]["needs"].append("add_browns")
                    plan["action"] = "recommend"

        # Calculate maturity for each bin
        for zone_id, bin_data in plan["bins"].items():
            temp = bin_data.get("temperature") or 20
            moisture = bin_data.get("moisture") or 50
            bin_data["maturity_pct"] = self._estimate_maturity_pct(temp, moisture)

        return plan

    async def act(self, plan: dict, hal: HAL) -> list[Trace]:
        """Write compost recommendations."""
        traces = []

        for zone_id, bin_data in plan.get("bins", {}).items():
            # Always write a status trace
            traces.append(
                self.make_trace(
                    TraceType.OBSERVATION,
                    {
                        "zone": zone_id,
                        "phase": bin_data.get("phase", "unknown"),
                        "maturity_pct": bin_data.get("maturity_pct", 0),
                        "temperature": bin_data.get("temperature"),
                        "moisture": bin_data.get("moisture"),
                    },
                    location=zone_id,
                )
            )

            for need in bin_data.get("needs", []):
                traces.append(
                    self.make_trace(
                        TraceType.RECOMMENDATION,
                        {
                            "recommendation": need,
                            "zone": zone_id,
                            "reason": self._explain_need(need, bin_data),
                        },
                        location=zone_id,
                        confidence=0.8,
                        ttl=7200,
                    )
                )

        return traces

    def _explain_need(self, need: str, bin_data: dict) -> str:
        explanations = {
            "turn_immediately": f"Temperature at {bin_data.get('temperature')}°C — risk of killing beneficial organisms",
            "add_greens": f"Temperature at {bin_data.get('temperature')}°C — add nitrogen-rich materials to restart heating",
            "add_water": f"Moisture at {bin_data.get('moisture')}% — decomposition slowed by dryness",
            "add_browns": f"Moisture at {bin_data.get('moisture')}% — excess moisture causing anaerobic conditions",
        }
        return explanations.get(need, need)

    async def reflect(self, action_traces: list[Trace]) -> list[Trace]:
        """Summarize compost cycle."""
        if not action_traces:
            return []

        return [
            self.make_trace(
                TraceType.OBSERVATION,
                {
                    "summary": "compost_cycle_complete",
                    "traces_written": len(action_traces),
                    "recommendations": [
                        t.payload.get("recommendation")
                        for t in action_traces
                        if t.type == TraceType.RECOMMENDATION
                    ],
                },
            )
        ]
