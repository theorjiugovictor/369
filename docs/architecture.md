# 369 Architecture

## Design Philosophy

369 is built on **stigmergy** — the principle of indirect coordination through shared environmental traces. Just as ants coordinate complex colony behavior by leaving pheromone trails, 369 agents coordinate by leaving traces on a shared bulletin board.

No agent ever communicates directly with another agent.

## System Layers

```
┌─────────────────────────────────────────────────────────┐
│                   API Layer (FastAPI)                     │
│          REST · WebSocket · Real-time events              │
├─────────────────────────────────────────────────────────┤
│                  Bulletin Board                           │
│     Redis (hot state) + PostgreSQL/TimescaleDB (warm)     │
│                                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │  Traces  │ │ Sensors  │ │  Events  │ │  State   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
├───────┬───────┬───────┬───────┬───────┬─────────────────┤
│       │       │       │       │       │                   │
│    ┌──▼─┐  ┌──▼──┐  ┌▼──┐  ┌▼───┐  ┌▼────────┐        │
│    │Soil│  │Irrig│  │Cmp│  │Wea.│  │Awareness│        │
│    └──┬─┘  └──┬──┘  └┬──┘  └┬───┘  └┬────────┘        │
│       │       │       │      │       │                   │
├───────▼───────▼───────▼──────▼───────▼───────────────────┤
│            Hardware Abstraction Layer (HAL)                │
│       MQTT · GPIO · HTTP · Mock (pluggable adapters)      │
├─────────────────────────────────────────────────────────┤
│                  Physical World                            │
│        Sensors · Actuators · ESP32 · Raspberry Pi         │
└─────────────────────────────────────────────────────────┘
```

## Agent Cycle

Every agent follows the same four-phase loop:

1. **Observe** — Read relevant traces and sensor data from the bulletin board
2. **Decide** — Analyze observations and produce a plan
3. **Act** — Execute the plan (write traces, optionally actuate hardware)
4. **Reflect** — Review actions taken and generate meta-traces

```python
async def cycle(self, bulletin, hal):
    observations = await self.observe(bulletin)
    plan = await self.decide(observations)
    action_traces = await self.act(plan, hal)
    await bulletin.write_traces(action_traces)
    reflections = await self.reflect(action_traces)
    await bulletin.write_traces(reflections)
```

## Data Flow

### Traces
Immutable records left by agents. Each trace has:
- `domain` — soil, water, compost, weather, energy, livestock, system
- `type` — observation, action, recommendation, alert
- `confidence` — 0.0 to 1.0
- `ttl` — optional time-to-live in seconds
- `references` — links to other trace IDs (for provenance)

### Sensor Readings
Time-series measurements from hardware:
- Stored in Redis (latest value per sensor)
- Persisted in TimescaleDB (full history)
- Queryable by sensor ID, zone, or metric

## Scale Profiles

| Scale | Agents | Hardware | Deployment |
|-------|--------|----------|------------|
| Backyard | 5 | Raspberry Pi + ESP32 | Docker Compose |
| Small Garden | 8 | Pi cluster | Docker Compose |
| Village | 15+ | Multiple nodes | K3s (lightweight Kubernetes) |

## Technology Choices

- **Python 3.12+** — async/await native, rich ecosystem
- **Redis** — sub-millisecond hot state, pub/sub for real-time events
- **PostgreSQL + TimescaleDB** — time-series optimized warm storage
- **MQTT** — lightweight IoT messaging for edge devices
- **FastAPI** — high-performance async REST + WebSocket
- **Pydantic v2** — data validation with zero-cost serialization
