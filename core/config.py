"""369 Configuration — YAML-based system configuration loader."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger("369.config")


class SensorConfig(BaseModel):
    id: str
    type: str
    adapter: str = "mock"
    topic: str | None = None


class ZoneConfig(BaseModel):
    id: str
    name: str
    type: str
    area_sqft: int | None = None
    sensors: list[SensorConfig] = Field(default_factory=list)


class AgentConfig(BaseModel):
    id: str
    type: str
    enabled: bool = True
    cycle_seconds: int = 300
    zones: list[str] = Field(default_factory=list)


class ActuatorConfig(BaseModel):
    id: str
    type: str
    adapter: str = "mock"
    topic: str | None = None
    zone: str | None = None


class LocationConfig(BaseModel):
    lat: float
    lon: float
    timezone: str = "UTC"


class SystemInfo(BaseModel):
    name: str
    scale: str = "backyard"
    location: LocationConfig = LocationConfig(lat=0, lon=0)


class HardwareConfig(BaseModel):
    adapters: dict[str, dict[str, Any]] = Field(default_factory=dict)


class SystemConfig(BaseModel):
    """Top-level system configuration."""

    system: SystemInfo
    zones: list[ZoneConfig] = Field(default_factory=list)
    agents: list[AgentConfig] = Field(default_factory=list)
    hardware: HardwareConfig = HardwareConfig()
    actuators: list[ActuatorConfig] = Field(default_factory=list)


def _expand_env_vars(data: Any) -> Any:
    """Recursively expand ${ENV_VAR} references in string values."""
    if isinstance(data, str) and data.startswith("${") and data.endswith("}"):
        var_name = data[2:-1]
        return os.environ.get(var_name, data)
    if isinstance(data, dict):
        return {k: _expand_env_vars(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_expand_env_vars(item) for item in data]
    return data


def load_config(path: str | Path) -> SystemConfig:
    """Load a YAML configuration file and return a validated SystemConfig."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    logger.info("Loading configuration from %s", path)
    with open(path) as f:
        raw = yaml.safe_load(f)

    expanded = _expand_env_vars(raw)
    return SystemConfig.model_validate(expanded)
