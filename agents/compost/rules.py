"""369 Compost Rules — Composting science and thresholds."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CompostPhase:
    name: str
    temp_min: float
    temp_max: float
    duration_days: tuple[int, int]  # (min, max)
    description: str


COMPOSTING_PHASES = [
    CompostPhase("mesophilic_start", 20, 40, (1, 5), "Initial colonization by mesophilic bacteria"),
    CompostPhase("thermophilic", 40, 70, (3, 21), "Peak decomposition — kills pathogens and weed seeds"),
    CompostPhase("mesophilic_end", 25, 40, (7, 14), "Cooling phase — fungi and actinomycetes take over"),
    CompostPhase("maturation", 15, 25, (21, 90), "Curing — humus formation and stabilization"),
]


def ideal_moisture_range() -> tuple[float, float]:
    """Optimal compost moisture: 40-60%."""
    return (40.0, 60.0)


def ideal_cn_ratio() -> tuple[float, float]:
    """Optimal carbon-to-nitrogen ratio: 25:1 to 30:1."""
    return (25.0, 30.0)


def needs_turning(temperature: float, days_since_turn: int) -> bool:
    """Determine if compost needs turning."""
    if temperature > 65:
        return True  # Too hot — turn to cool down
    if days_since_turn >= 7 and temperature > 40:
        return True  # Regular turning during thermophilic phase
    if days_since_turn >= 14:
        return True  # Turn at least every 2 weeks
    return False
