"""Activity feed list + POST + SSE stream (Phase 7 slice 1)."""

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies.db import DbSession
from app.schemas.activity import ActivityEventCreate, ActivityEventOut
from app.services.activity import (
    activity_out,
    activity_sse_stream,
    create_activity,
    list_activity,
)

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("", response_model=list[ActivityEventOut])
def api_list_activity(
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
):
    """Recent activity events, newest first."""
    return [activity_out(e) for e in list_activity(db, limit=limit)]


@router.post("", response_model=ActivityEventOut, status_code=201)
def api_create_activity(payload: ActivityEventCreate, db: DbSession):
    """Append an activity event (tests / manual emit)."""
    return activity_out(create_activity(db, payload))


@router.get("/stream")
async def api_activity_stream(
    heartbeat_seconds: float = Query(15.0, ge=0.05, le=120.0),
    max_seconds: float | None = Query(
        None,
        ge=0.05,
        le=3600.0,
        description="End stream after N seconds (tests / short demos).",
    ),
):
    """SSE: heartbeat frames + activity events as they are appended."""

    async def gen():
        async for chunk in activity_sse_stream(
            heartbeat_seconds=heartbeat_seconds,
            max_seconds=max_seconds,
        ):
            yield chunk

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
