"""369 API — Trace endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Request

from core.models import Trace, TraceDomain, TraceType

router = APIRouter()


@router.get("/")
async def list_traces(
    request: Request,
    domain: TraceDomain | None = None,
    trace_type: TraceType | None = None,
    limit: int = 50,
):
    """List traces with optional filtering."""
    bulletin = request.app.state.bulletin
    traces = await bulletin.read_traces(domain=domain, trace_type=trace_type, limit=limit)
    return {"traces": traces, "count": len(traces)}


@router.get("/domain/{domain}")
async def get_domain_traces(domain: TraceDomain, request: Request, limit: int = 50):
    """Get all traces for a specific domain."""
    bulletin = request.app.state.bulletin
    traces = await bulletin.read_traces(domain=domain, limit=limit)
    return {"domain": domain, "traces": traces, "count": len(traces)}


@router.post("/", status_code=201)
async def create_trace(trace: Trace, request: Request):
    """Manually write a trace (for testing or external integrations)."""
    bulletin = request.app.state.bulletin
    await bulletin.write_traces([trace])
    return {"status": "written", "trace_id": trace.id}
