"""369 Scheduler — Orchestrates agent cycles on configured intervals."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from core.bulletin import BulletinBoard
from core.config import AgentConfig, SystemConfig, load_config
from core.hal import HAL
from core.models import AgentStatus

logger = logging.getLogger("369.scheduler")

# Agent type → module path
AGENT_REGISTRY: dict[str, str] = {
    "soil": "agents.soil.agent.SoilAgent",
    "irrigation": "agents.irrigation.agent.IrrigationAgent",
    "compost": "agents.compost.agent.CompostAgent",
    "weather": "agents.weather.agent.WeatherAgent",
    "awareness": "agents.awareness.agent.AwarenessAgent",
}


def _import_agent_class(dotted_path: str):
    """Dynamically import an agent class from its dotted path."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class Scheduler:
    """Runs agent cycles on their configured intervals using asyncio."""

    def __init__(self, config: SystemConfig, bulletin: BulletinBoard, hal: HAL):
        self.config = config
        self.bulletin = bulletin
        self.hal = hal
        self._agents: dict[str, object] = {}
        self._tasks: list[asyncio.Task] = []
        self._running = True

    def _instantiate_agents(self) -> None:
        """Create agent instances from config."""
        for agent_cfg in self.config.agents:
            if not agent_cfg.enabled:
                logger.info("Skipping disabled agent: %s", agent_cfg.id)
                continue

            class_path = AGENT_REGISTRY.get(agent_cfg.type)
            if not class_path:
                logger.warning("Unknown agent type: %s", agent_cfg.type)
                continue

            try:
                agent_class = _import_agent_class(class_path)
                agent = agent_class(
                    agent_id=agent_cfg.id,
                    config={
                        "zones": agent_cfg.zones,
                        "cycle_seconds": agent_cfg.cycle_seconds,
                    },
                )
                self._agents[agent_cfg.id] = agent
                logger.info("Instantiated agent: %s (%s)", agent_cfg.id, agent_cfg.type)
            except Exception:
                logger.exception("Failed to instantiate agent: %s", agent_cfg.id)

    async def _run_agent_loop(self, agent, cycle_seconds: int) -> None:
        """Run a single agent's cycle on an interval."""
        while self._running:
            try:
                await agent.cycle(self.bulletin, self.hal)
                logger.info(
                    "Agent %s completed cycle, sleeping %ds",
                    agent.agent_id,
                    cycle_seconds,
                )
            except Exception:
                logger.exception("Agent %s cycle error", agent.agent_id)

            await asyncio.sleep(cycle_seconds)

    async def start(self) -> None:
        """Start all enabled agents on their cycle intervals."""
        self._instantiate_agents()

        for agent_cfg in self.config.agents:
            if not agent_cfg.enabled:
                continue
            agent = self._agents.get(agent_cfg.id)
            if agent:
                task = asyncio.create_task(
                    self._run_agent_loop(agent, agent_cfg.cycle_seconds),
                    name=f"agent-{agent_cfg.id}",
                )
                self._tasks.append(task)

        agent_count = len(self._tasks)
        logger.info(
            "Scheduler started with %d agents for '%s'",
            agent_count,
            self.config.system.name,
        )

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def stop(self) -> None:
        """Gracefully stop all agent loops."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("Scheduler stopped")


async def main(config_path: str, mock: bool = False) -> None:
    """Entry point for the scheduler."""
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    config = load_config(config_path)

    bulletin = BulletinBoard(
        redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379"),
        database_url=os.environ.get("DATABASE_URL", "postgresql://369:369@localhost:5432/three_six_nine"),
        mqtt_broker=os.environ.get("MQTT_BROKER", "localhost"),
    )
    await bulletin.connect()

    hal = HAL()

    if mock:
        from hal.adapters.mock import MockAdapter
        hal.register_adapter("mock", MockAdapter(seed=42))
        hal.register_adapter("mqtt", MockAdapter(seed=42))
        logger.info("Running in MOCK mode — all adapters use simulated data")

    # Register devices from config
    for zone in config.zones:
        for sensor in zone.sensors:
            hal.register_device({
                "id": sensor.id,
                "type": sensor.type,
                "adapter": "mock" if mock else sensor.adapter,
                "zone": zone.id,
                "topic": sensor.topic,
            })

    for actuator in config.actuators:
        hal.register_device({
            "id": actuator.id,
            "type": actuator.type,
            "adapter": "mock" if mock else actuator.adapter,
            "zone": actuator.zone,
            "topic": actuator.topic,
        })

    scheduler = Scheduler(config, bulletin, hal)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(scheduler.stop()))

    try:
        await scheduler.start()
    finally:
        await bulletin.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="369 Agent Scheduler")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    parser.add_argument("--mock", action="store_true", help="Use mock hardware adapters")
    args = parser.parse_args()

    asyncio.run(main(args.config, args.mock))
