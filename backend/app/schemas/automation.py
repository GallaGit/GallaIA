from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AutomationAction(BaseModel):
    """Lean action payload. Slice 2: create_task only."""

    type: Literal["create_task"] = "create_task"
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    assignee_agent: str | None = Field(
        default="default",
        description="Agent name to assign; session stub created when resolved",
    )


class AutomationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    interval_minutes: int
    enabled: bool
    last_fired_at: datetime | None = None
    action: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AutomationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    interval_minutes: int = Field(ge=1, le=525600)
    enabled: bool = True
    action: AutomationAction


class AutomationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    interval_minutes: int | None = Field(default=None, ge=1, le=525600)
    enabled: bool | None = None
    action: AutomationAction | None = None


class AutomationTickIn(BaseModel):
    """Optional test clock. Omit to use server UTC now."""

    now: datetime | None = None


class AutomationTickOut(BaseModel):
    now: datetime
    fired_automation_ids: list[int] = Field(default_factory=list)
    task_ids: list[int] = Field(default_factory=list)
    session_ids: list[int] = Field(default_factory=list)
    fired_count: int = 0
