"""369 API — Sensor reading endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from core.models import SensorReading

router = APIRouter()


@router.get("/{sensor_id}", response_model=SensorReading | None)
async def get_sensor_reading(sensor_id: str, request: Request):
    """Get the latest reading for a specific sensor."""
    bulletin = request.app.state.bulletin
    reading = await bulletin.read_sensor(sensor_id)
    if not reading:
        raise HTTPException(status_code=404, detail=f"No reading for sensor: {sensor_id}")
    return reading


@router.get("/zone/{zone_id}")
async def get_zone_readings(zone_id: str, request: Request, metric: str | None = None):
    """Get all sensor readings for a zone, optionally filtered by metric."""
    bulletin = request.app.state.bulletin
    readings = await bulletin.read_zone(zone_id, metric)
    return {"zone": zone_id, "readings": readings, "count": len(readings)}


@router.post("/", status_code=201)
async def post_sensor_reading(reading: SensorReading, request: Request):
    """Manually post a sensor reading (for testing or external integrations)."""
    bulletin = request.app.state.bulletin
    await bulletin.write_sensor_reading(reading)
    return {"status": "stored", "sensor_id": reading.sensor_id}
