"""F1.1 — Agent-to-agent threads and messages (backend only). F1.4 adds SSE streaming."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.dependencies.db import DbSession
from app.db.session import SessionLocal
from app.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models import Agent, Message, Project, Thread
from app.models.thread import HUMAN_ACTOR
from app.schemas import (
    DelegationEdgeOut,
    MessageCreate,
    MessageOut,
    ThreadAdvanceOut,
    ThreadCreate,
    ThreadDelegationsOut,
    ThreadDetailOut,
    ThreadOut,
    ThreadUpdate,
)
from app.services.activity import append_activity, notify_after_commit
from app.services.thread_agents import advance_thread as advance_thread_service
from app.services.thread_stream import thread_sse_stream

router = APIRouter(prefix="/threads", tags=["threads"])

DELEGATOR_ACTORS = {HUMAN_ACTOR, "orquestador"}


def _actor_pool(db: DbSession) -> set[str]:
    """Known agent slugs plus the human actor."""
    return set(db.scalars(select(Agent.name)).all()) | {HUMAN_ACTOR}


def _assert_actor(db: DbSession, value: str, field: str) -> None:
    if value not in _actor_pool(db):
        raise UnprocessableError(f"Unknown {field}: {value!r}")


@router.get("", response_model=list[ThreadOut])
def list_threads(db: DbSession, status: str | None = None):
    stmt = select(Thread).order_by(Thread.id.desc())
    if status is not None:
        stmt = stmt.where(Thread.status == status)
    return list(db.scalars(stmt).all())


@router.post("", response_model=ThreadOut, status_code=201)
def create_thread(payload: ThreadCreate, db: DbSession):
    if payload.project_id is not None and db.get(Project, payload.project_id) is None:
        raise NotFoundError(f"Project {payload.project_id} not found")
    _assert_actor(db, payload.created_by, "created_by")

    thread = Thread(
        title=payload.title,
        project_id=payload.project_id,
        created_by=payload.created_by,
        status="open",
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


@router.get("/{thread_id}", response_model=ThreadDetailOut)
def get_thread(thread_id: int, db: DbSession):
    thread = db.get(Thread, thread_id)
    if thread is None:
        raise NotFoundError(f"Thread {thread_id} not found")
    messages = list(
        db.scalars(
            select(Message)
            .where(Message.thread_id == thread_id)
            .order_by(Message.created_at, Message.id)
        ).all()
    )
    return ThreadDetailOut(
        **ThreadOut.model_validate(thread).model_dump(),
        messages=[MessageOut.model_validate(m) for m in messages],
    )


@router.patch("/{thread_id}", response_model=ThreadOut)
def update_thread(thread_id: int, payload: ThreadUpdate, db: DbSession):
    thread = db.get(Thread, thread_id)
    if thread is None:
        raise NotFoundError(f"Thread {thread_id} not found")
    thread.status = payload.status
    db.commit()
    db.refresh(thread)
    return thread


@router.post("/{thread_id}/messages", response_model=MessageOut, status_code=201)
def create_message(thread_id: int, payload: MessageCreate, db: DbSession):
    thread = db.get(Thread, thread_id)
    if thread is None:
        raise NotFoundError(f"Thread {thread_id} not found")
    if thread.status == "closed":
        raise ConflictError(f"Thread {thread_id} is closed")

    _assert_actor(db, payload.sender, "sender")
    if payload.recipient is not None:
        _assert_actor(db, payload.recipient, "recipient")
    if payload.kind == "delegation" and payload.sender not in DELEGATOR_ACTORS:
        raise UnprocessableError("Only orquestador or user may send kind=delegation")

    message = Message(
        thread_id=thread.id,
        sender=payload.sender,
        recipient=payload.recipient,
        kind=payload.kind,
        body=payload.body,
    )
    db.add(message)
    db.flush()
    evt = append_activity(
        db,
        type="message.created",
        message=f"Message in thread {thread.id} from {message.sender}",
    )
    db.commit()
    db.refresh(message)
    notify_after_commit(evt)
    return message


@router.post("/{thread_id}/advance", response_model=ThreadAdvanceOut)
def advance_thread(
    thread_id: int,
    db: DbSession,
    max_steps: int = Query(6, ge=1, le=20),
):
    thread = db.get(Thread, thread_id)
    if thread is None:
        raise NotFoundError(f"Thread {thread_id} not found")
    created = advance_thread_service(db, thread, max_steps=max_steps)
    return ThreadAdvanceOut(created=[MessageOut.model_validate(m) for m in created])


@router.get("/{thread_id}/delegations", response_model=ThreadDelegationsOut)
def get_thread_delegations(thread_id: int, db: DbSession):
    thread = db.get(Thread, thread_id)
    if thread is None:
        raise NotFoundError(f"Thread {thread_id} not found")
    messages = list(
        db.scalars(
            select(Message)
            .where(Message.thread_id == thread_id)
            .order_by(Message.created_at, Message.id)
        ).all()
    )
    delegations = [
        m for m in messages if m.sender == "orquestador" and m.kind == "delegation"
    ]
    used_result_ids: set[int] = set()
    edges: list[DelegationEdgeOut] = []
    for delegation in delegations:
        match = next(
            (
                m
                for m in messages
                if m.kind == "result"
                and m.sender == delegation.recipient
                and m.recipient == "orquestador"
                and m.id > delegation.id
                and m.id not in used_result_ids
            ),
            None,
        )
        if match is not None:
            used_result_ids.add(match.id)
        edges.append(
            DelegationEdgeOut(
                delegation_id=delegation.id,
                source=delegation.sender,
                target=delegation.recipient or "",
                brief=delegation.body,
                status="answered" if match is not None else "pending",
                result_id=match.id if match is not None else None,
                result_body=match.body if match is not None else None,
            )
        )
    summary_id: int | None = None
    if delegations:
        last_delegation_id = delegations[-1].id
        for m in messages:
            if (
                m.sender == "orquestador"
                and m.recipient == "user"
                and m.kind == "text"
                and m.id > last_delegation_id
            ):
                summary_id = m.id
    return ThreadDelegationsOut(
        thread_id=thread.id,
        nodes=["user", "orquestador", "fe", "be"],
        edges=edges,
        summary_id=summary_id,
    )


@router.get("/{thread_id}/stream")
async def stream_thread(
    thread_id: int,
    request: Request,
    db: DbSession,
    max_steps: int = Query(6, ge=1, le=20),
    heartbeat_seconds: float = Query(15.0, ge=0.05, le=120.0),
    max_seconds: float | None = Query(
        None,
        ge=0.05,
        le=3600.0,
        description="End stream after N seconds (tests / short demos).",
    ),
):
    """SSE (F1.4): replay thread messages, then stream advance_thread output live.

    Uses the deterministic mock LLM, so no API key is needed. Mirrors the
    error contract of POST /advance: 404 when missing, 409 when closed.
    """
    thread = db.get(Thread, thread_id)
    if thread is None:
        raise NotFoundError(f"Thread {thread_id} not found")
    if thread.status == "closed":
        raise ConflictError(f"Thread {thread_id} is closed")

    # Prefer the same sessionmaker the app uses (request.app.state or db bind).
    factory = getattr(request.app.state, "session_factory", None) or SessionLocal

    async def gen():
        async for chunk in thread_sse_stream(
            session_factory=factory,
            thread_id=thread_id,
            max_steps=max_steps,
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
