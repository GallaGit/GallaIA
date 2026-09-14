from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    status: str
    dod_items: list[str] = Field(default_factory=list)
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    dod_items: list[str] = Field(default_factory=list, min_length=1)
    project_id: int | None = None


class GoalSpawnOut(BaseModel):
    """Stub spawn: placeholder session linked to the goal (orchestrator later)."""

    goal_id: int
    goal_status: str
    session_id: int
    task_id: int | None = None
