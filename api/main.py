"""369 API — Main FastAPI application."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import agents, insights, sensors, traces

load_dotenv()

logger = logging.getLogger("369.api")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    from core.bulletin import BulletinBoard

    bulletin = BulletinBoard(
        redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379"),
        database_url=os.environ.get("DATABASE_URL", "postgresql://369:369@localhost:5432/three_six_nine"),
        mqtt_broker=os.environ.get("MQTT_BROKER", "localhost"),
    )
    await bulletin.connect()
    app.state.bulletin = bulletin
    logger.info("369 API started")

    yield

    await bulletin.close()
    logger.info("369 API shutdown")


app = FastAPI(
    title="369 API",
    description="REST and WebSocket interface for the 369 regenerative intelligence system",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sensors.router, prefix="/api/sensors", tags=["sensors"])
app.include_router(traces.router, prefix="/api/traces", tags=["traces"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(insights.router, prefix="/api/insights", tags=["insights"])


@app.get("/health")
async def health():
    return {"status": "healthy", "system": "369"}
