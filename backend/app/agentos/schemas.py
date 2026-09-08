"""Pydantic API schemas for AgentOS MVP."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

KanbanStatus = Literal["todo", "doing", "review", "done"]
RunnerKind = Literal["mock", "anthropic", "openrouter"]


class AgentSeedOut(BaseModel):
    name: str
    title: str
    model: str
    one_job: str
    skills: list[str]
    mcp: list[str]
    runner_preference: str
    prompt_origin: str
    foundational_prompt: str
    role_prompt: str


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    assignee_agent: str = "default"


class TaskUpdate(BaseModel):
    assignee_agent: str | None = None
    status: KanbanStatus | None = None


class TaskOut(BaseModel):
    id: str
    name: str
    description: str
    assignee_agent: str
    status: KanbanStatus
    activity: list[str]
    created_at: datetime
    updated_at: datetime


class ToolEventOut(BaseModel):
    name: str
    input: dict[str, Any]
    output: dict[str, Any]
    at: datetime


class SessionOut(BaseModel):
    id: str
    task_id: str
    agent_name: str
    runner: RunnerKind
    status: str
    summary: str
    tool_events: list[ToolEventOut]
    started_at: datetime
    ended_at: datetime | None


class RunRequest(BaseModel):
    agent_name: str | None = None
    runner: RunnerKind | None = None


class RunResponse(BaseModel):
    runner: RunnerKind
    used_anthropic: bool
    used_openrouter: bool = False
    summary: str
    task: TaskOut
    session: SessionOut


class InboxItem(BaseModel):
    id: str
    kind: Literal["session", "task"]
    task_id: str
    title: str
    status: str
    message: str
    created_at: datetime
