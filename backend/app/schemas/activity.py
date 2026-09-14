"""Activity feed schemas (Phase 7)."""

from datetime import datetime

from pydantic import BaseModel, Field


class ActivityEventOut(BaseModel):
    id: int
    type: str
    message: str
    task_id: int | None = None
    session_id: int | None = None
    automation_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityEventCreate(BaseModel):
    type: str = Field(..., min_length=1, max_length=80)
    message: str = Field(..., min_length=1)
    task_id: int | None = None
    session_id: int | None = None
    automation_id: int | None = None
