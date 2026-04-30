"""Tests for the BulletinBoard — trace and sensor operations."""

from __future__ import annotations

import pytest

from core.models import SensorReading, Trace, TraceDomain, TraceType


class FakeRedis:
    """Minimal Redis mock for testing."""

    def __init__(self):
        self._store: dict[str, str | list] = {}
        self._hash_store: dict[str, dict[str, str]] = {}
        self._published: list[tuple[str, str]] = []

    def pipeline(self):
        return FakePipeline(self)

    async def set(self, key, value, ex=None):
        self._store[key] = value

    async def get(self, key):
        return self._store.get(key)

    async def hset(self, key, field, value):
        self._hash_store.setdefault(key, {})[field] = value

    async def hgetall(self, key):
        return self._hash_store.get(key, {})

    async def lrange(self, key, start, end):
        data = self._store.get(key, [])
        if isinstance(data, list):
            return data[start:end + 1]
        return []

    async def publish(self, channel, message):
        self._published.append((channel, message))

    async def aclose(self):
        pass


class FakePipeline:
    def __init__(self, redis: FakeRedis):
        self._redis = redis
        self._ops = []

    def lpush(self, key, value):
        if key not in self._redis._store or not isinstance(self._redis._store[key], list):
            self._redis._store[key] = []
        self._redis._store[key].insert(0, value)

    def ltrim(self, key, start, end):
        if key in self._redis._store and isinstance(self._redis._store[key], list):
            self._redis._store[key] = self._redis._store[key][start:end + 1]

    def set(self, key, value, ex=None):
        self._redis._store[key] = value

    def publish(self, channel, message):
        self._redis._published.append((channel, message))

    async def execute(self):
        pass


class FakePool:
    """Minimal asyncpg pool mock."""

    def __init__(self):
        self._executed = []

    def acquire(self):
        return FakeConnection(self)

    async def close(self):
        pass


class FakeConnection:
    def __init__(self, pool):
        self._pool = pool

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def execute(self, query, *args):
        self._pool._executed.append(("execute", query, args))

    async def executemany(self, query, args):
        self._pool._executed.append(("executemany", query, args))

    async def fetch(self, query, *args):
        return []


@pytest.fixture
def bulletin():
    """Create a BulletinBoard with fake backends."""
    from core.bulletin import BulletinBoard

    board = BulletinBoard(
        redis_url="redis://fake",
        database_url="postgresql://fake",
    )
    board._redis = FakeRedis()
    board._pg_pool = FakePool()
    return board


def test_trace_creation():
    """Test Trace model creates valid instances."""
    trace = Trace(
        agent_id="test-agent",
        type=TraceType.OBSERVATION,
        domain=TraceDomain.SOIL,
        payload={"moisture": 45.2, "zone": "raised-beds"},
    )
    assert trace.agent_id == "test-agent"
    assert trace.type == TraceType.OBSERVATION
    assert trace.domain == TraceDomain.SOIL
    assert trace.confidence == 1.0
    assert trace.id  # UUID generated


@pytest.mark.asyncio
async def test_write_traces(bulletin):
    """Test writing traces to bulletin board."""
    traces = [
        Trace(
            agent_id="soil-agent",
            type=TraceType.OBSERVATION,
            domain=TraceDomain.SOIL,
            payload={"moisture": 42.0, "zone": "raised-beds"},
        ),
        Trace(
            agent_id="soil-agent",
            type=TraceType.ALERT,
            domain=TraceDomain.SOIL,
            payload={"alert": "low_moisture"},
        ),
    ]
    await bulletin.write_traces(traces)

    # Verify Redis got the traces
    assert "369:traces:soil" in bulletin._redis._store


@pytest.mark.asyncio
async def test_read_traces_from_redis(bulletin):
    """Test reading traces returns data from Redis."""
    trace = Trace(
        agent_id="test",
        type=TraceType.OBSERVATION,
        domain=TraceDomain.WATER,
        payload={"test": True},
    )
    await bulletin.write_traces([trace])
    results = await bulletin.read_traces(domain=TraceDomain.WATER)
    assert len(results) == 1
    assert results[0].agent_id == "test"


@pytest.mark.asyncio
async def test_sensor_reading_write_read(bulletin):
    """Test writing and reading sensor data."""
    reading = SensorReading(
        sensor_id="soil-moisture-rb-1",
        metric="soil.moisture",
        value=48.5,
        unit="%",
        zone="raised-beds",
    )
    await bulletin.write_sensor_reading(reading)
    result = await bulletin.read_sensor("soil-moisture-rb-1")
    assert result is not None
    assert result.value == 48.5
    assert result.zone == "raised-beds"


@pytest.mark.asyncio
async def test_read_zone(bulletin):
    """Test reading all sensors for a zone."""
    readings = [
        SensorReading(sensor_id="s1", metric="soil.moisture", value=45.0, unit="%", zone="zone-a"),
        SensorReading(sensor_id="s2", metric="soil.temperature", value=18.0, unit="°C", zone="zone-a"),
    ]
    for r in readings:
        await bulletin.write_sensor_reading(r)

    results = await bulletin.read_zone("zone-a")
    assert len(results) == 2


@pytest.mark.asyncio
async def test_write_empty_traces(bulletin):
    """Writing empty list should be a no-op."""
    await bulletin.write_traces([])
    assert "369:traces:soil" not in bulletin._redis._store
