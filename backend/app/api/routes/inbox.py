"""Inbox decisions — list open items; human reply / resolve (Phase 7 slice 2)."""

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies.db import DbSession
from app.exceptions import BadRequestError, NotFoundError
from app.models import InboxMessage
from app.schemas import InboxMessageOut, InboxReplyIn
from app.schemas.inbox import InboxResolveIn
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
