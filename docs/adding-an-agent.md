# Adding a New Agent to 369

## Overview

Every 369 agent extends the `Agent369` base class and implements four methods:
`observe`, `decide`, `act`, and `reflect`.

## Step-by-Step

### 1. Create the agent directory

```bash
mkdir -p agents/your_domain/
```

### 2. Implement the agent class

Create `agents/your_domain/agent.py`:

```python
from core.agent import Agent369
from core.bulletin import BulletinBoard
from core.hal import HAL
from core.models import Trace, TraceDomain, TraceType


class YourAgent(Agent369):
    def __init__(self, agent_id: str = "your-agent", config=None):
        super().__init__(
            agent_id=agent_id,
            domain=TraceDomain.SOIL,  # choose your domain
            config=config,
        )

    async def observe(self, bulletin: BulletinBoard) -> list[Trace]:
        """Read relevant data from the bulletin board."""
        readings = await bulletin.read_zone("your-zone", "your.metric")
        return [self.make_trace(TraceType.OBSERVATION, {"data": r.value}) for r in readings]

    async def decide(self, observations: list[Trace]) -> dict:
        """Analyze and produce a plan."""
        return {"action": "do_something", "data": observations}

    async def act(self, plan: dict, hal: HAL) -> list[Trace]:
        """Execute plan. Write traces. Optionally actuate hardware."""
        result = await hal.actuate("your-actuator", {"action": "on"})
        return [self.make_trace(TraceType.ACTION, {"result": result.success})]

    async def reflect(self, action_traces: list[Trace]) -> list[Trace]:
        """Review and learn."""
        return [self.make_trace(TraceType.OBSERVATION, {"summary": "done"})]
```

### 3. Create config.yaml

Create `agents/your_domain/config.yaml`:

```yaml
agent:
  type: your_domain
  domain: soil
  description: "What this agent does"

thresholds:
  # Domain-specific thresholds
```

### 4. Register in the scheduler

Add to `AGENT_REGISTRY` in `core/scheduler.py`:

```python
AGENT_REGISTRY = {
    ...
    "your_domain": "agents.your_domain.agent.YourAgent",
}
```

### 5. Add to your config YAML

In `config/backyard.yaml` (or your scale config):

```yaml
agents:
  - id: your-agent
    type: your_domain
    enabled: true
    cycle_seconds: 300
    zones: [your-zone]
```

## Design Principles

1. **Never talk to other agents directly** — use the bulletin board
2. **Be a good citizen** — set appropriate TTL on traces
3. **Include confidence scores** — especially for recommendations
4. **Reference your sources** — use the `references` field
5. **Fail gracefully** — catch errors, log, continue
