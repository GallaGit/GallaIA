from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    project_id: int | None = None
    assignee_agent_id: int | None = None
    approval_gate: bool = False


class TaskUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    assignee_agent_id: int | None = None
    approval_gate: bool | None = None


class TaskStatusUpdate(BaseModel):
    status: str = Field(pattern="^(todo|doing|review|done)$")


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    description: str | None = None
    status: str
    assignee_agent_id: int | None = None
    approval_gate: bool
    created_at: datetime
    updated_at: datetime
