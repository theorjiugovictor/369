"""369 Bulletin Board — Shared stigmergic state."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import asyncpg
import redis.asyncio as redis

from core.models import SensorReading, Trace, TraceDomain, TraceType

if TYPE_CHECKING:
    pass

logger = logging.getLogger("369.bulletin")


class BulletinBoard:
    """Shared state store for stigmergic agent coordination.

    Hot state (recent traces, sensor readings) lives in Redis.
    Warm state (historical traces) persists in PostgreSQL/TimescaleDB.
    """

    def __init__(self, redis_url: str, database_url: str, mqtt_broker: str | None = None):
        self._redis_url = redis_url
        self._database_url = database_url
        self._mqtt_broker = mqtt_broker
        self._redis: redis.Redis | None = None
        self._pg_pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Initialize connections to Redis and PostgreSQL."""
        logger.info("Connecting bulletin board to Redis at %s", self._redis_url)
        self._redis = redis.from_url(self._redis_url, decode_responses=True)

        logger.info("Connecting bulletin board to PostgreSQL")
        self._pg_pool = await asyncpg.create_pool(self._database_url, min_size=2, max_size=10)

        await self._ensure_schema()
        logger.info("Bulletin board connected and schema ready")

    async def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        async with self._pg_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    type TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    payload JSONB NOT NULL DEFAULT '{}',
                    ttl INTEGER,
                    location TEXT,
                    confidence FLOAT NOT NULL DEFAULT 1.0,
                    references_ TEXT[] DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_traces_domain ON traces(domain);
                CREATE INDEX IF NOT EXISTS idx_traces_timestamp ON traces(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_traces_agent ON traces(agent_id);
                CREATE INDEX IF NOT EXISTS idx_traces_type ON traces(type);

                CREATE TABLE IF NOT EXISTS sensor_readings (
                    sensor_id TEXT NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    metric TEXT NOT NULL,
                    value DOUBLE PRECISION NOT NULL,
                    unit TEXT NOT NULL,
                    zone TEXT,
                    PRIMARY KEY (sensor_id, timestamp)
                );
                CREATE INDEX IF NOT EXISTS idx_sensor_zone ON sensor_readings(zone);
            """)

    async def close(self) -> None:
        """Shut down connections."""
        if self._redis:
            await self._redis.aclose()
        if self._pg_pool:
            await self._pg_pool.close()
        logger.info("Bulletin board connections closed")

    # ── Trace Operations ──────────────────────────────────────────

    async def write_traces(self, traces: list[Trace]) -> None:
        """Write traces to both hot (Redis) and warm (PostgreSQL) stores."""
        if not traces:
            return

        # Redis — hot state (keyed by domain, capped at last 500 per domain)
        pipe = self._redis.pipeline()
        for trace in traces:
            trace_json = trace.model_dump_json()
            key = f"369:traces:{trace.domain.value}"
            pipe.lpush(key, trace_json)
            pipe.ltrim(key, 0, 499)

            # Also publish for real-time subscribers
            pipe.publish(f"369:events:{trace.domain.value}", trace_json)

            if trace.ttl:
                pipe.set(f"369:trace:{trace.id}", trace_json, ex=trace.ttl)
        await pipe.execute()

        # PostgreSQL — warm state
        async with self._pg_pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO traces (id, agent_id, timestamp, type, domain, payload, ttl, location, confidence, references_)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (id) DO NOTHING
                """,
                [
                    (
                        t.id, t.agent_id, t.timestamp, t.type.value, t.domain.value,
                        json.dumps(t.payload), t.ttl, t.location, t.confidence, t.references,
                    )
                    for t in traces
                ],
            )

        logger.debug("Wrote %d traces to bulletin board", len(traces))

    async def read_traces(
        self,
        domain: TraceDomain | None = None,
        since: datetime | None = None,
        trace_type: TraceType | None = None,
        limit: int = 100,
    ) -> list[Trace]:
        """Read traces, preferring Redis for recent data, falling back to PostgreSQL."""
        # Try Redis first for recent traces
        if domain and not since and not trace_type:
            raw = await self._redis.lrange(f"369:traces:{domain.value}", 0, limit - 1)
            if raw:
                return [Trace.model_validate_json(r) for r in raw]

        # Fall back to PostgreSQL for filtered queries
        conditions = []
        params = []
        idx = 1

        if domain:
            conditions.append(f"domain = ${idx}")
            params.append(domain.value)
            idx += 1

        if since:
            conditions.append(f"timestamp >= ${idx}")
            params.append(since)
            idx += 1

        if trace_type:
            conditions.append(f"type = ${idx}")
            params.append(trace_type.value)
            idx += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT * FROM traces {where} ORDER BY timestamp DESC LIMIT {limit}"

        async with self._pg_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [
            Trace(
                id=r["id"],
                agent_id=r["agent_id"],
                timestamp=r["timestamp"],
                type=TraceType(r["type"]),
                domain=TraceDomain(r["domain"]),
                payload=json.loads(r["payload"]) if isinstance(r["payload"], str) else r["payload"],
                ttl=r["ttl"],
                location=r["location"],
                confidence=r["confidence"],
                references=r["references_"] or [],
            )
            for r in rows
        ]

    # ── Sensor Operations ─────────────────────────────────────────

    async def write_sensor_reading(self, reading: SensorReading) -> None:
        """Store a sensor reading in both Redis (latest) and PostgreSQL (history)."""
        reading_json = reading.model_dump_json()

        # Redis — always holds latest reading per sensor
        await self._redis.set(f"369:sensor:{reading.sensor_id}", reading_json)

        if reading.zone:
            await self._redis.hset(
                f"369:zone:{reading.zone}",
                reading.sensor_id,
                reading_json,
            )

        # PostgreSQL — time series
        async with self._pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sensor_readings (sensor_id, timestamp, metric, value, unit, zone)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (sensor_id, timestamp) DO UPDATE SET value = $4
                """,
                reading.sensor_id, reading.timestamp, reading.metric,
                reading.value, reading.unit, reading.zone,
            )

    async def read_sensor(self, sensor_id: str) -> SensorReading | None:
        """Get the latest reading for a sensor."""
        raw = await self._redis.get(f"369:sensor:{sensor_id}")
        if raw:
            return SensorReading.model_validate_json(raw)
        return None

    async def read_zone(self, zone: str, metric: str | None = None) -> list[SensorReading]:
        """Get all latest sensor readings for a zone, optionally filtered by metric."""
        raw_map = await self._redis.hgetall(f"369:zone:{zone}")
        readings = [SensorReading.model_validate_json(v) for v in raw_map.values()]
        if metric:
            readings = [r for r in readings if r.metric == metric]
        return readings

    # ── Pub/Sub ───────────────────────────────────────────────────

    async def publish_event(self, domain: str, event: dict) -> None:
        """Publish a real-time event on the bulletin board."""
        await self._redis.publish(f"369:events:{domain}", json.dumps(event))

    async def subscribe_events(self, domain: str):
        """Subscribe to real-time events for a domain. Yields parsed events."""
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(f"369:events:{domain}")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield json.loads(message["data"])
        finally:
            await pubsub.unsubscribe(f"369:events:{domain}")
