"""369 API — Agent management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from core.models import AgentState, AgentStatus

router = APIRouter()


@router.get("/")
async def list_agents(request: Request):
    """List all configured agents and their status."""
    # In a full implementation, this would read from scheduler state
    # For now, return status from Redis if available
    bulletin = request.app.state.bulletin
    if bulletin._redis:
        keys = []
        async for key in bulletin._redis.scan_iter("369:agent:*"):
            keys.append(key)
        return {"agents": keys, "count": len(keys)}
    return {"agents": [], "count": 0}


@router.get("/{agent_id}/state")
async def get_agent_state(agent_id: str, request: Request):
    """Get the current state of a specific agent."""
    bulletin = request.app.state.bulletin
    if bulletin._redis:
        state_raw = await bulletin._redis.get(f"369:agent:{agent_id}")
        if state_raw:
            return AgentState.model_validate_json(state_raw)

    return {"agent_id": agent_id, "status": "unknown"}


@router.get("/{agent_id}/traces")
async def get_agent_traces(agent_id: str, request: Request, limit: int = 20):
    """Get recent traces written by a specific agent."""
    bulletin = request.app.state.bulletin
    # Query PostgreSQL for agent-specific traces
    all_traces = await bulletin.read_traces(limit=limit * 5)
    agent_traces = [t for t in all_traces if t.agent_id == agent_id][:limit]
    return {"agent_id": agent_id, "traces": agent_traces, "count": len(agent_traces)}
