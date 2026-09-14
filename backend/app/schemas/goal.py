from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    status: str
    dod_items: list[str] = Field(default_factory=list)
    dod_checked: list[bool] = Field(default_factory=list)
    spend_cap: float | None = None
    spend_accrued: float = 0.0
    max_wall_seconds: int | None = None
    stuck_threshold: int = 19
    activated_at: datetime | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    dod_items: list[str] = Field(default_factory=list, min_length=1)
    project_id: int | None = None
    spend_cap: float | None = None
    max_wall_seconds: int | None = Field(default=None, ge=1)
    stuck_threshold: int = Field(default=19, ge=2)


class GoalSpawnOut(BaseModel):
    """Stub spawn: placeholder session linked to the goal."""

    goal_id: int
    goal_status: str
    session_id: int
    task_id: int | None = None


class GoalOrchestrateOut(BaseModel):
    """One orchestrator step: complete open session, check DoD, spawn next or finish."""

    goal_id: int
    goal_status: str
    action: str  # spawned | done | stuck | noop
    session_id: int | None = None
    task_id: int | None = None
    dod_checked: list[bool] = Field(default_factory=list)
    detail: str | None = None
