"""F1.1 — Agent-to-agent threads and messages (backend only)."""

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.dependencies.db import DbSession
from app.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models import Agent, Message, Project, Thread
from app.models.thread import HUMAN_ACTOR
from app.schemas import (
    MessageCreate,
    MessageOut,
    ThreadAdvanceOut,
    ThreadCreate,
    ThreadDetailOut,
    ThreadOut,
    ThreadUpdate,
)
from app.services.activity import append_activity, notify_after_commit
from app.services.thread_agents import advance_thread as advance_thread_service

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
