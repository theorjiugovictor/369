# 369 — The Living Intelligence for Regenerative Systems

A stigmergic multi-agent operating system for regenerative living. Agents coordinate through shared state — never communicating directly — to manage soil, water, compost, weather, and energy across any scale from a single backyard to an entire village.

## Quick Start

```bash
# Clone and configure
git clone https://github.com/theorjiugovictor/369.git
cd 369
cp .env.example .env
# Edit .env with your settings

# Start all services
docker compose up -d

# Run in mock mode (no hardware needed)
python -m core.scheduler --config config/backyard.yaml --mock
```

## Architecture

369 follows a **stigmergic** coordination model inspired by how ant colonies self-organize:

```
┌─────────────────────────────────────────────┐
│              Bulletin Board                  │
│         (Redis + PostgreSQL)                 │
│                                              │
│  Traces: observations, actions, alerts       │
│  Sensors: real-time readings                 │
│  Events: pub/sub notifications               │
└──────┬──────┬──────┬──────┬──────┬──────────┘
       │      │      │      │      │
    ┌──▼─┐ ┌──▼──┐ ┌─▼──┐ ┌▼───┐ ┌▼────────┐
    │Soil│ │Water│ │Comp│ │Wea.│ │Awareness│
    └──┬─┘ └──┬──┘ └─┬──┘ └┬───┘ └┬────────┘
       │      │      │     │      │
    ┌──▼──────▼──────▼─────▼──────▼──────────┐
    │     Hardware Abstraction Layer (HAL)     │
    │   MQTT · GPIO · HTTP · Mock adapters     │
    └─────────────────────────────────────────┘
```

Each agent follows a **observe → decide → act → reflect** cycle, reading from and writing to the shared bulletin board. No agent ever talks to another directly.

## Project Structure

- `core/` — Bulletin board, agent base class, HAL interface, scheduler
- `agents/` — Domain agents (soil, irrigation, compost, weather, awareness)
- `hal/` — Hardware abstraction with pluggable adapters
- `api/` — FastAPI REST + WebSocket interface
- `config/` — Scale-specific configurations (backyard, garden, village)
- `docs/` — Architecture docs, guides, and references
- `tests/` — Test suite

## Scale Profiles

| Profile | Zones | Agents | Hardware |
|---------|-------|--------|----------|
| Backyard | 2-4 | 5 | Raspberry Pi + ESP32 |
| Small Garden | 4-8 | 8 | Pi cluster |
| Village | 10+ | 15+ | K3s cluster |

## Documentation

- [Architecture](docs/architecture.md)
- [Adding an Agent](docs/adding-an-agent.md)
- [Hardware Guide](docs/hardware-guide.md)
- [Deployment](docs/deployment.md)

## License

Apache 2.0
