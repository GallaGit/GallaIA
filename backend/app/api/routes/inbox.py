from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies.db import DbSession
from app.exceptions import BadRequestError, NotFoundError
from app.models import InboxMessage
from app.schemas import InboxMessageOut, InboxReplyIn

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("", response_model=list[InboxMessageOut])
def list_inbox(db: DbSession, status: str | None = None):
    stmt = select(InboxMessage).order_by(InboxMessage.id.desc())
    if status is not None:
        stmt = stmt.where(InboxMessage.status == status)
    return list(db.scalars(stmt).all())


@router.post("/{message_id}/reply", response_model=InboxMessageOut)
def reply_inbox(message_id: int, payload: InboxReplyIn, db: DbSession):
    msg = db.get(InboxMessage, message_id)
    if msg is None:
        raise NotFoundError(f"Inbox message {message_id} not found")
    if msg.status not in ("open",):
        raise BadRequestError("Message is not open")
    msg.reply_body = payload.body
    msg.status = "answered"
    msg.answered_at = datetime.now(timezone.utc)
    # Phase 1 stub: does not resume a live session (no real container).
    db.commit()
    db.refresh(msg)
    return msg
