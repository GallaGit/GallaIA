"""In-memory domain objects for AgentOS MVP (no DB yet)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

KanbanStatus = Literal["todo", "doing", "review", "done"]
SessionStatus = Literal[
    "starting", "running", "waiting-inbox", "destroyed", "failed"
]
RunnerKind = Literal["mock", "anthropic"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass
class ToolEvent:
    name: str
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    at: datetime = field(default_factory=_utcnow)


@dataclass
class Task:
    name: str
    description: str = ""
    assignee_agent: str = "default"
    status: KanbanStatus = "todo"
    id: str = field(default_factory=lambda: _new_id("task"))
    activity: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def touch(self) -> None:
        self.updated_at = _utcnow()


@dataclass
class Session:
    task_id: str
    agent_name: str
    runner: RunnerKind
    id: str = field(default_factory=lambda: _new_id("sess"))
    status: SessionStatus = "starting"
    tool_events: list[ToolEvent] = field(default_factory=list)
    summary: str = ""
    started_at: datetime = field(default_factory=_utcnow)
    ended_at: datetime | None = None
