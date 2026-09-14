from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InboxMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_role: str
    agent_id: int | None = None
    session_id: int | None = None
    task_id: int | None = None
    kind: str
    body: str
    status: str
    reply_body: str | None = None
    created_at: datetime
    answered_at: datetime | None = None


class InboxReplyIn(BaseModel):
    """Human reply that resolves an open inbox decision."""

    body: str = Field(min_length=1)


class InboxResolveIn(BaseModel):
    """Resolve without a long reply (optional short note)."""

    note: str | None = Field(default=None, max_length=2000)
