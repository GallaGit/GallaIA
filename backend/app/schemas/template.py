from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.task import TaskOut


class TemplateStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    name: str
    description: str | None = None
    assignee_agent_name: str | None = None
    approval_gate: bool
    requires_previous_done: bool


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    slug: str
    name: str
    description: str | None = None
    created_at: datetime
    steps: list[TemplateStepOut] = Field(default_factory=list)


class TemplateInstantiateIn(BaseModel):
    """Optional overrides when materializing a template into task cards."""

    project_id: int | None = None
    name_prefix: str | None = Field(default=None, max_length=80)


class TemplateInstantiateOut(BaseModel):
    template_id: int
    template_slug: str
    run_id: str
    tasks: list[TaskOut]
