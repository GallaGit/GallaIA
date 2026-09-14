"""Sessions list/get + live SSE viewer (Phase 7 slice 3)."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.dependencies.db import DbSession
from app.exceptions import NotFoundError
from app.models import AgentSession
from app.schemas import SessionOut
from app.services.session_stream import session_sse_stream

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionOut])
def list_sessions(db: DbSession, task_id: int | None = None, agent_id: int | None = None):
    stmt = select(AgentSession).order_by(AgentSession.id.desc())
    if task_id is not None:
        stmt = stmt.where(AgentSession.task_id == task_id)
    if agent_id is not None:
        stmt = stmt.where(AgentSession.agent_id == agent_id)
    return list(db.scalars(stmt).all())


@router.get("/{session_id}/stream")
async def api_session_stream(
    session_id: int,
    request: Request,
    poll_seconds: float = Query(0.25, ge=0.05, le=30.0),
    heartbeat_seconds: float = Query(15.0, ge=0.05, le=120.0),
    max_seconds: float | None = Query(
        None,
        ge=0.05,
        le=3600.0,
        description="End stream after N seconds (tests / short demos).",
    ),
):
    """SSE: session status + tool-log lines (replay then poll DB) + heartbeats."""
    # Prefer the same sessionmaker the app uses (request.app.state or db bind).
    from app.db.session import SessionLocal

    factory = getattr(request.app.state, "session_factory", None) or SessionLocal

    async def gen():
        async for chunk in session_sse_stream(
            session_factory=factory,
            session_id=session_id,
            poll_seconds=poll_seconds,
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


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: DbSession):
    session = db.get(AgentSession, session_id)
    if session is None:
        raise NotFoundError(f"Session {session_id} not found")
    return session
