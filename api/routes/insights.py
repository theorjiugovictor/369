"""369 API — Insights and briefing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from core.models import TraceDomain, TraceType

router = APIRouter()


@router.get("/briefing")
async def get_daily_briefing(request: Request):
    """Get the latest daily briefing from the awareness agent."""
    bulletin = request.app.state.bulletin
    traces = await bulletin.read_traces(domain=TraceDomain.SYSTEM, limit=10)

    briefings = [
        t for t in traces
        if t.payload.get("type") == "daily_briefing"
    ]

    if briefings:
        latest = briefings[0]
        return {
            "timestamp": latest.timestamp.isoformat(),
            "source": latest.payload.get("source", "unknown"),
            "insight": latest.payload.get("insight", ""),
            "domains_analyzed": latest.payload.get("domains_analyzed", []),
        }

    return {"message": "No briefing available yet"}


@router.get("/alerts")
async def get_active_alerts(request: Request):
    """Get all active alerts across all domains."""
    bulletin = request.app.state.bulletin
    alerts = await bulletin.read_traces(trace_type=TraceType.ALERT, limit=50)
    return {
        "alerts": alerts,
        "count": len(alerts),
        "domains": list({a.domain.value for a in alerts}),
    }


@router.get("/recommendations")
async def get_recommendations(request: Request, domain: TraceDomain | None = None):
    """Get active recommendations, optionally filtered by domain."""
    bulletin = request.app.state.bulletin
    recs = await bulletin.read_traces(
        domain=domain,
        trace_type=TraceType.RECOMMENDATION,
        limit=50,
    )
    return {"recommendations": recs, "count": len(recs)}
