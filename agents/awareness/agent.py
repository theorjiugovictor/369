"""369 Awareness Agent — Cross-system reasoning with Claude."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from core.agent import Agent369
from core.bulletin import BulletinBoard
from core.hal import HAL
from core.models import Trace, TraceDomain, TraceType

logger = logging.getLogger("369.agent.awareness")


class AwarenessAgent(Agent369):
    """READ-ONLY meta-agent that observes all domains and generates insights.

    Uses Anthropic's Claude API for cross-system reasoning.
    Never actuates hardware — only writes observation and recommendation traces.
    """

    DOMAINS_TO_OBSERVE = [
        TraceDomain.SOIL,
        TraceDomain.WATER,
        TraceDomain.COMPOST,
        TraceDomain.WEATHER,
        TraceDomain.ENERGY,
        TraceDomain.LIVESTOCK,
    ]

    def __init__(self, agent_id: str = "awareness-agent", config: dict[str, Any] | None = None):
        super().__init__(agent_id=agent_id, domain=TraceDomain.SYSTEM, config=config)
        self._api_key = os.environ.get("ANTHROPIC_API_KEY")
        self._client = None

    @property
    def capabilities(self) -> list[str]:
        return ["cross_domain.analysis", "daily.briefing", "anomaly.detection"]

    def _get_client(self):
        """Lazily initialize Anthropic client."""
        if self._client is None and self._api_key and self._api_key != "your-key-here":
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
            except ImportError:
                logger.warning("anthropic package not installed — awareness agent will use fallback")
        return self._client

    async def observe(self, bulletin: BulletinBoard) -> list[Trace]:
        """Read traces from ALL domains for cross-system awareness."""
        all_traces = []

        for domain in self.DOMAINS_TO_OBSERVE:
            traces = await bulletin.read_traces(domain=domain, limit=20)
            all_traces.extend(traces)

        # Also read recent alerts from any domain
        alerts = await bulletin.read_traces(trace_type=TraceType.ALERT, limit=20)
        all_traces.extend(alerts)

        return all_traces

    async def decide(self, observations: list[Trace]) -> dict:
        """Use Claude (or fallback heuristics) to analyze cross-domain patterns."""
        plan = {"action": "analyze", "observations_count": len(observations)}

        if not observations:
            plan["action"] = "idle"
            return plan

        # Build context summary
        domain_summaries = {}
        alerts = []

        for trace in observations:
            domain = trace.domain.value
            domain_summaries.setdefault(domain, []).append(trace.payload)
            if trace.type == TraceType.ALERT:
                alerts.append(trace.payload)

        plan["domain_summaries"] = domain_summaries
        plan["active_alerts"] = alerts

        # Try Claude for deeper analysis
        client = self._get_client()
        if client:
            try:
                insight = await self._analyze_with_claude(domain_summaries, alerts)
                plan["claude_insight"] = insight
            except Exception:
                logger.exception("Claude analysis failed — using fallback")
                plan["claude_insight"] = None
        else:
            plan["claude_insight"] = None

        # Fallback heuristic analysis
        plan["heuristic_insights"] = self._heuristic_analysis(domain_summaries, alerts)

        return plan

    async def _analyze_with_claude(self, summaries: dict, alerts: list) -> str:
        """Send system state to Claude for cross-domain reasoning."""
        prompt = (
            "You are the awareness agent for a regenerative garden system called 369. "
            "Analyze the following sensor data and agent observations across domains. "
            "Identify patterns, potential issues, and opportunities.\n\n"
        )

        for domain, entries in summaries.items():
            prompt += f"## {domain.upper()} Domain\n"
            for entry in entries[:5]:  # Limit to avoid token overload
                prompt += f"- {entry}\n"
            prompt += "\n"

        if alerts:
            prompt += "## ACTIVE ALERTS\n"
            for alert in alerts:
                prompt += f"- {alert}\n"

        prompt += (
            "\nProvide a brief daily briefing (3-5 bullet points) covering:\n"
            "1. Overall system health\n"
            "2. Cross-domain interactions noticed\n"
            "3. Actionable recommendations\n"
            "4. Any concerning patterns"
        )

        response = await self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def _heuristic_analysis(self, summaries: dict, alerts: list) -> list[str]:
        """Simple rule-based cross-domain analysis as Claude fallback."""
        insights = []

        # Check soil + weather interaction
        soil_data = summaries.get("soil", [])
        weather_data = summaries.get("weather", [])

        low_moisture_zones = []
        for entry in soil_data:
            if entry.get("metric") == "soil.moisture" and entry.get("value", 100) < 30:
                low_moisture_zones.append(entry.get("zone", "unknown"))

        rain_expected = any(
            entry.get("precipitation_mm", 0) > 5
            for entry in weather_data
        )

        if low_moisture_zones and rain_expected:
            insights.append(
                f"Zones {low_moisture_zones} are dry but rain is expected — "
                "irrigation may be deferred to conserve water."
            )
        elif low_moisture_zones and not rain_expected:
            insights.append(
                f"Zones {low_moisture_zones} are dry with no rain forecasted — "
                "irrigation should be prioritized."
            )

        # Check compost health
        compost_data = summaries.get("compost", [])
        for entry in compost_data:
            if entry.get("maturity_pct", 0) > 80:
                insights.append(
                    f"Compost in {entry.get('zone', 'unknown')} is nearing maturity — "
                    "plan for harvest and application to garden beds."
                )

        if alerts:
            insights.append(f"{len(alerts)} active alert(s) require attention.")

        if not insights:
            insights.append("System operating normally. No cross-domain issues detected.")

        return insights

    async def act(self, plan: dict, hal: HAL) -> list[Trace]:
        """Write insights and daily briefing — NEVER actuate hardware."""
        traces = []

        if plan["action"] == "idle":
            return traces

        # Claude insight trace
        if plan.get("claude_insight"):
            traces.append(
                self.make_trace(
                    TraceType.OBSERVATION,
                    {
                        "type": "daily_briefing",
                        "source": "claude",
                        "insight": plan["claude_insight"],
                        "domains_analyzed": list(plan.get("domain_summaries", {}).keys()),
                    },
                    confidence=0.7,
                    ttl=86400,
                )
            )

        # Heuristic insights
        for insight in plan.get("heuristic_insights", []):
            traces.append(
                self.make_trace(
                    TraceType.RECOMMENDATION,
                    {
                        "type": "cross_domain_insight",
                        "source": "heuristic",
                        "insight": insight,
                    },
                    confidence=0.6,
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
                    "summary": "awareness_cycle_complete",
                    "insights_generated": len(action_traces),
                    "used_claude": any(
                        t.payload.get("source") == "claude" for t in action_traces
                    ),
                },
            )
        ]
