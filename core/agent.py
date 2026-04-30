"""369 Agent Base — The stigmergic agent contract."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from core.models import AgentState, AgentStatus, Trace, TraceDomain, TraceType

if TYPE_CHECKING:
    from core.bulletin import BulletinBoard
    from core.hal import HAL

logger = logging.getLogger("369.agent")


class Agent369(ABC):
    """Abstract base class for all 369 agents.

    Every agent follows the stigmergic cycle:
        observe → decide → act → reflect

    Agents never communicate directly. All coordination happens
    through traces left on the shared BulletinBoard.
    """

    def __init__(self, agent_id: str, domain: TraceDomain, config: dict[str, Any] | None = None):
        self.agent_id = agent_id
        self.domain = domain
        self.config = config or {}
        self.status = AgentStatus.ACTIVE
        self._logger = logging.getLogger(f"369.agent.{agent_id}")

    @property
    def state(self) -> AgentState:
        return AgentState(
            agent_id=self.agent_id,
            status=self.status,
            last_heartbeat=datetime.now(timezone.utc),
            capabilities=self.capabilities,
        )

    @property
    def capabilities(self) -> list[str]:
        """Override to declare agent capabilities."""
        return []

    # ── The Stigmergic Cycle ──────────────────────────────────────

    @abstractmethod
    async def observe(self, bulletin: BulletinBoard) -> list[Trace]:
        """Read the bulletin board for relevant signals."""
        ...

    @abstractmethod
    async def decide(self, observations: list[Trace]) -> dict:
        """Produce a plan based on observations."""
        ...

    @abstractmethod
    async def act(self, plan: dict, hal: HAL) -> list[Trace]:
        """Execute the plan, possibly actuating hardware."""
        ...

    @abstractmethod
    async def reflect(self, action_traces: list[Trace]) -> list[Trace]:
        """Review actions taken and generate meta-traces (learning, alerts)."""
        ...

    async def cycle(self, bulletin: BulletinBoard, hal: HAL) -> None:
        """Run one full observe → decide → act → reflect loop."""
        self._logger.info("Starting cycle for %s", self.agent_id)
        self.status = AgentStatus.ACTIVE

        try:
            observations = await self.observe(bulletin)
            self._logger.debug("Observed %d traces", len(observations))

            plan = await self.decide(observations)
            self._logger.debug("Plan: %s", plan.get("action", "none"))

            action_traces = await self.act(plan, hal)
            if action_traces:
                await bulletin.write_traces(action_traces)
                self._logger.info("Wrote %d action traces", len(action_traces))

            reflections = await self.reflect(action_traces)
            if reflections:
                await bulletin.write_traces(reflections)
                self._logger.debug("Wrote %d reflection traces", len(reflections))

        except Exception:
            self.status = AgentStatus.ERROR
            self._logger.exception("Cycle failed for %s", self.agent_id)
            raise

    # ── Helpers ────────────────────────────────────────────────────

    def make_trace(
        self,
        trace_type: TraceType,
        payload: dict[str, Any],
        location: str | None = None,
        confidence: float = 1.0,
        ttl: int | None = None,
        references: list[str] | None = None,
    ) -> Trace:
        """Create a trace stamped with this agent's identity."""
        return Trace(
            agent_id=self.agent_id,
            type=trace_type,
            domain=self.domain,
            payload=payload,
            location=location,
            confidence=confidence,
            ttl=ttl,
            references=references or [],
        )
