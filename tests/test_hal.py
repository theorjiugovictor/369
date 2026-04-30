"""Tests for HAL and mock adapter."""

from __future__ import annotations

import pytest

from core.hal import HAL, ActuationResult
from core.models import SensorReading
from hal.adapters.mock import MockAdapter


@pytest.fixture
def hal_with_mock():
    """Create a HAL instance with mock adapter and registered devices."""
    hal = HAL()
    mock = MockAdapter(seed=42)
    hal.register_adapter("mock", mock)

    # Register test devices
    hal.register_device({
        "id": "test-moisture-1",
        "type": "soil_moisture",
        "adapter": "mock",
        "zone": "test-zone",
    })
    hal.register_device({
        "id": "test-temp-1",
        "type": "soil_temperature",
        "adapter": "mock",
        "zone": "test-zone",
    })
    hal.register_device({
        "id": "test-valve-1",
        "type": "solenoid_valve",
        "adapter": "mock",
        "zone": "test-zone",
    })

    return hal


@pytest.mark.asyncio
async def test_read_sensor(hal_with_mock):
    """Test reading a sensor through HAL."""
    reading = await hal_with_mock.read_sensor("test-moisture-1")
    assert isinstance(reading, SensorReading)
    assert reading.sensor_id == "test-moisture-1"
    assert reading.metric == "soil.moisture"
    assert reading.unit == "%"
    assert 0 <= reading.value <= 100


@pytest.mark.asyncio
async def test_read_sensor_unknown():
    """Test reading an unknown sensor raises KeyError."""
    hal = HAL()
    with pytest.raises(KeyError, match="Unknown sensor"):
        await hal.read_sensor("nonexistent")


@pytest.mark.asyncio
async def test_actuate(hal_with_mock):
    """Test actuating through HAL."""
    result = await hal_with_mock.actuate("test-valve-1", {"action": "on", "duration": 300})
    assert isinstance(result, ActuationResult)
    assert result.success is True
    assert result.actuator_id == "test-valve-1"


@pytest.mark.asyncio
async def test_actuate_unknown():
    """Test actuating an unknown device."""
    hal = HAL()
    result = await hal.actuate("nonexistent", {"action": "on"})
    assert result.success is False
    assert "Unknown" in result.message


@pytest.mark.asyncio
async def test_health_check(hal_with_mock):
    """Test HAL health check."""
    health = await hal_with_mock.health_check()
    assert "adapters" in health
    assert "mock" in health["adapters"]
    assert health["adapters"]["mock"]["status"] == "healthy"
    assert health["devices"] == 3


@pytest.mark.asyncio
async def test_mock_adapter_deterministic():
    """Test that mock adapter with same seed produces consistent ranges."""
    mock = MockAdapter(seed=123)
    device_config = {"type": "soil_moisture", "zone": "test"}

    readings = []
    for _ in range(10):
        r = await mock.read_sensor("test-sensor", device_config)
        readings.append(r.value)

    # All values should be within valid range for soil moisture
    assert all(0 <= v <= 100 for v in readings)
    # Should have some variation (not all the same)
    assert len(set(readings)) > 1


@pytest.mark.asyncio
async def test_mock_adapter_different_sensor_types():
    """Test mock adapter handles different sensor types correctly."""
    mock = MockAdapter(seed=42)

    moisture = await mock.read_sensor("s1", {"type": "soil_moisture", "zone": "z1"})
    assert moisture.metric == "soil.moisture"
    assert moisture.unit == "%"

    temp = await mock.read_sensor("s2", {"type": "soil_temperature", "zone": "z1"})
    assert temp.metric == "soil.temperature"
    assert temp.unit == "°C"

    compost_temp = await mock.read_sensor("s3", {"type": "temperature", "zone": "z2"})
    assert compost_temp.metric == "temperature"
    assert compost_temp.unit == "°C"
