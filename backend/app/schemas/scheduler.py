from datetime import datetime

from pydantic import BaseModel, Field


class SchedulerTickIn(BaseModel):
    """Optional test clock. Omit to use server UTC now."""

    now: datetime | None = None


class SchedulerTickOut(BaseModel):
    now: datetime
    promoted_task_ids: list[int] = Field(default_factory=list)
    session_ids: list[int] = Field(default_factory=list)
    promoted_count: int = 0
