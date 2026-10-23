"""Inbox decisions — list open items; human reply / resolve / approve (Phase 7)."""

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies.db import DbSession
from app.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import InboxMessage, Thread
from app.runtime import thread_graph
from app.schemas import InboxDecideIn, InboxDecideOut, InboxMessageOut, InboxReplyIn
from app.schemas.inbox import InboxResolveIn
from app.schemas.thread import MessageOut
from app.services import thread_agents
from app.services.activity import append_activity, notify_after_commit

router = APIRouter(prefix="/inbox", tags=["inbox"])


def _close_message(
    db: DbSession,
    msg: InboxMessage,
    *,
    reply_body: str | None,
    activity_type: str,
    activity_message: str,
) -> InboxMessage:
    msg.reply_body = reply_body
    msg.status = "answered"
    msg.answered_at = datetime.now(timezone.utc)
    evt = append_activity(
        db,
        type=activity_type,
        message=activity_message,
        task_id=msg.task_id,
        session_id=msg.session_id,
    )
    # Phase 1/7 stub: does not resume a live session (no real container yet).
    db.commit()
    db.refresh(msg)
    notify_after_commit(evt)
    return msg


@router.get("", response_model=list[InboxMessageOut])
def list_inbox(db: DbSession, status: str | None = None):
    """List inbox decision messages (newest first). Filter by status=open|answered."""
    stmt = select(InboxMessage).order_by(InboxMessage.id.desc())
    if status is not None:
        stmt = stmt.where(InboxMessage.status == status)
    return list(db.scalars(stmt).all())


@router.get("/{message_id}", response_model=InboxMessageOut)
def get_inbox_message(message_id: int, db: DbSession):
    msg = db.get(InboxMessage, message_id)
    if msg is None:
        raise NotFoundError(f"Inbox message {message_id} not found")
    return msg


@router.post("/{message_id}/reply", response_model=InboxMessageOut)
def reply_inbox(message_id: int, payload: InboxReplyIn, db: DbSession):
    """Human reply — marks the decision answered and emits activity."""
    msg = db.get(InboxMessage, message_id)
    if msg is None:
        raise NotFoundError(f"Inbox message {message_id} not found")
    if msg.kind == "thread_approval":
        raise BadRequestError("Thread approvals must use /decide")
    if msg.status != "open":
        raise BadRequestError("Message is not open")
    return _close_message(
        db,
        msg,
        reply_body=payload.body,
        activity_type="inbox.replied",
        activity_message=f"Inbox #{msg.id} replied",
    )


@router.post("/{message_id}/resolve", response_model=InboxMessageOut)
def resolve_inbox(message_id: int, payload: InboxResolveIn, db: DbSession):
    """Resolve an open decision (optional short note) without a full reply body."""
    msg = db.get(InboxMessage, message_id)
    if msg is None:
        raise NotFoundError(f"Inbox message {message_id} not found")
    if msg.kind == "thread_approval":
        raise BadRequestError("Thread approvals must use /decide")
    if msg.status != "open":
        raise BadRequestError("Message is not open")
    note = (payload.note or "").strip() or None
    return _close_message(
        db,
        msg,
        reply_body=note,
        activity_type="inbox.resolved",
        activity_message=f"Inbox #{msg.id} resolved",
    )


@router.post("/{message_id}/decide", response_model=InboxDecideOut)
def decide_inbox(message_id: int, payload: InboxDecideIn, db: DbSession):
    """Human decision for a thread approval; resumes the paused LangGraph."""
    msg = db.get(InboxMessage, message_id)
    if msg is None:
        raise NotFoundError(f"Inbox message {message_id} not found")
    if msg.status != "open":
        raise BadRequestError("Message is not open")
    if msg.kind != "thread_approval":
        raise BadRequestError("Message is not a thread approval")
    if msg.thread_id is None:
        raise BadRequestError("Thread approval is missing its thread")

    thread = db.get(Thread, msg.thread_id)
    if thread is None:
        raise NotFoundError(f"Thread {msg.thread_id} not found")
    if thread.status == "closed":
        raise ConflictError(f"Thread {thread.id} is closed")

    llm = thread_agents.default_llm(db, thread.id, thread.project_id)
    created, events = thread_graph.resume_thread_approval(
        db, thread, msg, payload.approved, payload.note, llm
    )

    note = (payload.note or "").strip() or None
    msg.reply_body = note
    msg.status = "answered"
    msg.answered_at = datetime.now(timezone.utc)
    evt = append_activity(
        db,
        type="inbox.decided",
        message=f"Inbox #{msg.id} decided",
        task_id=msg.task_id,
        session_id=msg.session_id,
    )
    db.commit()
    db.refresh(msg)
    for reply in created:
        db.refresh(reply)
    notify_after_commit(evt)
    for event in events:
        notify_after_commit(event)
    return InboxDecideOut(
        inbox=InboxMessageOut.model_validate(msg),
        created=[MessageOut.model_validate(m) for m in created],
    )
