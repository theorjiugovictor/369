"""Tests for Agent369 base class and cycle."""

from __future__ import annotations

import pytest

from core.agent import Agent369
from core.bulletin import BulletinBoard
from core.hal import HAL
from core.models import AgentStatus, Trace, TraceDomain, TraceType


class MockAgent(Agent369):
    """Test agent for verifying the cycle."""

    def __init__(self):
        super().__init__(agent_id="mock-agent", domain=TraceDomain.SOIL)
        self.observed = False
        self.decided = False
        self.acted = False
        self.reflected = False

    @property
    def capabilities(self) -> list[str]:
        return ["mock.test"]

    async def observe(self, bulletin) -> list[Trace]:
        self.observed = True
        return [
            self.make_trace(TraceType.OBSERVATION, {"test": "observation"})
        ]

    async def decide(self, observations) -> dict:
        self.decided = True
        return {"action": "test", "observations_count": len(observations)}

    async def act(self, plan, hal) -> list[Trace]:
        self.acted = True
        return [
            self.make_trace(TraceType.ACTION, {"test": "action"})
        ]

    async def reflect(self, action_traces) -> list[Trace]:
        self.reflected = True
        return [
            self.make_trace(TraceType.OBSERVATION, {"test": "reflection"})
        ]


class FakeBulletin:
    """Minimal bulletin mock for agent testing."""

    def __init__(self):
        self.written_traces: list[Trace] = []

    async def write_traces(self, traces):
        self.written_traces.extend(traces)

    async def read_traces(self, **kwargs):
        return []

    async def read_zone(self, zone, metric=None):
        return []

    async def read_sensor(self, sensor_id):
        return None


class FakeHAL:
    """Minimal HAL mock for agent testing."""

    def __init__(self):
        self.actuations: list[tuple] = []

    async def read_sensor(self, sensor_id):
        from core.models import SensorReading
        return SensorReading(
            sensor_id=sensor_id, metric="test", value=42.0, unit="test"
        )

    async def actuate(self, actuator_id, command):
        from core.hal import ActuationResult
        self.actuations.append((actuator_id, command))
        return ActuationResult(actuator_id=actuator_id, success=True, message="mock")


def test_agent_state():
    """Test agent state reporting."""
    agent = MockAgent()
    state = agent.state
    assert state.agent_id == "mock-agent"
    assert state.status == AgentStatus.ACTIVE
    assert "mock.test" in state.capabilities


def test_make_trace():
    """Test trace creation helper."""
    agent = MockAgent()
    trace = agent.make_trace(
        TraceType.OBSERVATION,
        {"key": "value"},
        location="zone-1",
        confidence=0.9,
    )
    assert trace.agent_id == "mock-agent"
    assert trace.domain == TraceDomain.SOIL
    assert trace.type == TraceType.OBSERVATION
    assert trace.payload == {"key": "value"}
    assert trace.location == "zone-1"
    assert trace.confidence == 0.9


@pytest.mark.asyncio
async def test_agent_cycle():
    """Test the full observe → decide → act → reflect cycle."""
    agent = MockAgent()
    bulletin = FakeBulletin()
    hal = FakeHAL()

    await agent.cycle(bulletin, hal)

    assert agent.observed
    assert agent.decided
    assert agent.acted
    assert agent.reflected
    # action traces + reflection traces should be written
    assert len(bulletin.written_traces) == 2


@pytest.mark.asyncio
async def test_agent_cycle_writes_traces():
    """Verify traces are written to bulletin board during cycle."""
    agent = MockAgent()
    bulletin = FakeBulletin()
    hal = FakeHAL()

    await agent.cycle(bulletin, hal)

    action_traces = [t for t in bulletin.written_traces if t.type == TraceType.ACTION]
    reflection_traces = [t for t in bulletin.written_traces if t.type == TraceType.OBSERVATION]

    assert len(action_traces) == 1
    assert len(reflection_traces) == 1
    assert action_traces[0].payload == {"test": "action"}
