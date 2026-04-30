"""369 Data Models — Traces, sensor readings, and agent state."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TraceDomain(str, Enum):
    SOIL = "soil"
    WATER = "water"
    ENERGY = "energy"
    COMPOST = "compost"
    LIVESTOCK = "livestock"
    WEATHER = "weather"
    SYSTEM = "system"


class TraceType(str, Enum):
    OBSERVATION = "observation"
    ACTION = "action"
    RECOMMENDATION = "recommendation"
    ALERT = "alert"


class AgentStatus(str, Enum):
    ACTIVE = "active"
    DORMANT = "dormant"
    ERROR = "error"


class Trace(BaseModel):
    """An immutable record left by an agent on the bulletin board."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    type: TraceType
    domain: TraceDomain
    payload: dict[str, Any] = Field(default_factory=dict)
    ttl: int | None = None  # seconds; None = permanent
    location: str | None = None  # zone id
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    references: list[str] = Field(default_factory=list)  # trace IDs


class SensorReading(BaseModel):
    """A single sensor measurement."""

    sensor_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metric: str  # e.g. "soil.moisture"
    value: float
    unit: str
    zone: str | None = None


class AgentState(BaseModel):
    """Runtime state of an agent."""

    agent_id: str
    status: AgentStatus = AgentStatus.ACTIVE
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_plan: dict[str, Any] | None = None
    capabilities: list[str] = Field(default_factory=list)
