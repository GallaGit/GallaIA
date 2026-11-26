"""Inbox decisions — list open items; human reply / resolve / approve (Phase 7)."""

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies.db import DbSession
from app.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import InboxMessage, Message, Thread
from app.runtime import thread_graph
from app.schemas import InboxDecideIn, InboxDecideOut, InboxMessageOut, InboxReplyIn
from app.schemas.inbox import InboxResolveIn
from app.schemas.thread import MessageOut
from app.services import thread_agents
from app.services.activity import append_activity, notify_after_commit, publish_inbox

router = APIRouter(prefix="/inbox", tags=["inbox"])


def _target_agent(db: DbSession, msg: InboxMessage) -> str | None:
    if msg.thread_message_id is None:
        return None
    linked = db.get(Message, msg.thread_message_id)
    if linked is None:
        return None
    return linked.recipient


def _inbox_out(db: DbSession, msg: InboxMessage) -> InboxMessageOut:
    data = InboxMessageOut.model_validate(msg)
    return data.model_copy(update={"target_agent": _target_agent(db, msg)})


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
    rows = list(db.scalars(stmt).all())
    return [_inbox_out(db, m) for m in rows]


@router.get("/{message_id}", response_model=InboxMessageOut)
def get_inbox_message(message_id: int, db: DbSession):
    msg = db.get(InboxMessage, message_id)
    if msg is None:
        raise NotFoundError(f"Inbox message {message_id} not found")
    return _inbox_out(db, msg)


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
    return _inbox_out(
        db,
        _close_message(
            db,
            msg,
            reply_body=payload.body,
            activity_type="inbox.replied",
            activity_message=f"Inbox #{msg.id} replied",
        ),
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
    return _inbox_out(
        db,
        _close_message(
            db,
            msg,
            reply_body=note,
            activity_type="inbox.resolved",
            activity_message=f"Inbox #{msg.id} resolved",
        ),
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

    target = _target_agent(db, msg)
    llm = thread_agents.default_llm(db, thread.id, thread.project_id)
    created, events, signals = thread_graph.resume_thread_approval(
        db, thread, msg, payload.approved, payload.note, llm
    )

    note = (payload.note or "").strip() or None
    msg.reply_body = note
    msg.status = "answered"
    msg.answered_at = datetime.now(timezone.utc)
    decision_label = "approved" if payload.approved else "rejected"
    evt = append_activity(
        db,
        type="inbox.decided",
        message=(
            f"Inbox #{msg.id} decided · {decision_label}"
            + (f" · target={target}" if target else "")
        ),
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
    publish_inbox(
        {
            "action": "decided",
            "inbox_id": msg.id,
            "kind": msg.kind,
            "status": msg.status,
            "thread_id": msg.thread_id,
            "thread_message_id": msg.thread_message_id,
            "target_agent": target,
            "approved": bool(payload.approved),
            "body": msg.body,
        }
    )
    for signal in signals:
        publish_inbox(signal)
    return InboxDecideOut(
        inbox=_inbox_out(db, msg),
        created=[MessageOut.model_validate(m) for m in created],
    )
