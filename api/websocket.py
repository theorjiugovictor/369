"""369 API — WebSocket for real-time trace streaming."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from core.models import TraceDomain

logger = logging.getLogger("369.api.websocket")


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, domain: str = "all"):
        await websocket.accept()
        self._connections.setdefault(domain, []).append(websocket)
        logger.info("WebSocket client connected (domain=%s)", domain)

    def disconnect(self, websocket: WebSocket, domain: str = "all"):
        if domain in self._connections:
            self._connections[domain] = [
                ws for ws in self._connections[domain] if ws != websocket
            ]

    async def broadcast(self, domain: str, message: dict):
        """Broadcast a message to all subscribers of a domain."""
        targets = self._connections.get(domain, []) + self._connections.get("all", [])
        disconnected = []

        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)

        # Clean up disconnected
        for ws in disconnected:
            self.disconnect(ws, domain)


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, domain: str = "all"):
    """WebSocket endpoint for real-time trace streaming.

    Connect to /ws/{domain} to receive traces for a specific domain,
    or /ws/all for everything.
    """
    await manager.connect(websocket, domain)
    try:
        while True:
            # Keep connection alive; client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, domain)
        logger.info("WebSocket client disconnected (domain=%s)", domain)
