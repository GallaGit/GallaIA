"""Phase 5 named automations — interval schedule + test-clock tick.

Lean: ``interval_minutes`` only (no croniter). Due when enabled and
``last_fired_at`` is None or ``last_fired_at + interval <= now``.
Action ``create_task`` creates a task + optional session stub (runner=automation).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError, NotFoundError
from app.models import Agent, AgentSession, Project, Task
from app.models.automation import Automation
from app.schemas.automation import (
    AutomationAction,
    AutomationCreate,
    AutomationOut,
    AutomationTickOut,
    AutomationUpdate,
)

RUNNER = "automation"


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_action(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def automation_out(row: Automation) -> AutomationOut:
    return AutomationOut(
        id=row.id,
        name=row.name,
        interval_minutes=row.interval_minutes,
        enabled=row.enabled,
        last_fired_at=row.last_fired_at,
        action=_parse_action(row.action_json),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def list_automations(db: Session) -> list[Automation]:
    return list(db.scalars(select(Automation).order_by(Automation.id)).all())


def get_automation(db: Session, automation_id: int) -> Automation:
    row = db.get(Automation, automation_id)
    if row is None:
        raise NotFoundError(f"Automation {automation_id} not found")
    return row


def create_automation(db: Session, payload: AutomationCreate) -> Automation:
    existing = db.scalar(select(Automation).where(Automation.name == payload.name))
    if existing is not None:
        raise BadRequestError(f"Automation name {payload.name!r} already exists")
    row = Automation(
        name=payload.name.strip(),
        interval_minutes=payload.interval_minutes,
        enabled=payload.enabled,
        action_json=payload.action.model_dump_json(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_automation(
    db: Session, automation_id: int, payload: AutomationUpdate
) -> Automation:
    row = get_automation(db, automation_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestError("No fields to update")
    if "name" in data and data["name"] is not None:
        name = data["name"].strip()
        clash = db.scalar(
            select(Automation).where(Automation.name == name, Automation.id != row.id)
        )
        if clash is not None:
            raise BadRequestError(f"Automation name {name!r} already exists")
        row.name = name
    if "interval_minutes" in data and data["interval_minutes"] is not None:
        row.interval_minutes = data["interval_minutes"]
    if "enabled" in data and data["enabled"] is not None:
        row.enabled = data["enabled"]
    if "action" in data and data["action"] is not None:
        action = payload.action
        assert action is not None
        row.action_json = action.model_dump_json()
    db.commit()
    db.refresh(row)
    return row


def delete_automation(db: Session, automation_id: int) -> None:
    row = get_automation(db, automation_id)
    db.delete(row)
    db.commit()


def is_due(row: Automation, clock: datetime) -> bool:
    """Return True when enabled and interval has elapsed (or never fired)."""
    if not row.enabled:
        return False
    if row.interval_minutes < 1:
        return False
    if row.last_fired_at is None:
        return True
    next_at = _as_utc(row.last_fired_at) + timedelta(minutes=row.interval_minutes)
    return next_at <= clock


def _default_project(db: Session) -> Project:
    project = db.scalar(select(Project).where(Project.slug == "default"))
    if project is None:
        raise BadRequestError("Default project missing; seed the database first")
    return project


def _resolve_agent(db: Session, name: str | None) -> Agent | None:
    if not name:
        return None
    agent = db.scalar(select(Agent).where(Agent.name == name))
    if agent is None:
        agent = db.scalar(select(Agent).order_by(Agent.id.asc()))
    return agent


def _fire_create_task(
    db: Session, row: Automation, action: dict[str, Any]
) -> tuple[int, int | None]:
    """Execute create_task action. Returns (task_id, session_id|None)."""
    try:
        validated = AutomationAction.model_validate(action)
    except Exception as exc:  # noqa: BLE001 — surface as 400-ish via BadRequest
        raise BadRequestError(f"Invalid automation action: {exc}") from exc

    project = _default_project(db)
    agent = _resolve_agent(db, validated.assignee_agent)

    task = Task(
        project_id=project.id,
        name=validated.name[:200],
        description=validated.description
        or f"Created by automation {row.name!r}",
        status="todo",
        assignee_agent_id=agent.id if agent else None,
    )
    db.add(task)
    db.flush()

    session_id: int | None = None
    if agent is not None:
        stub = AgentSession(
            agent_id=agent.id,
            task_id=task.id,
            runner=RUNNER,
            status="queued",
            summary=f"automation fire name={row.name}",
            tool_call_log="[]",
        )
        db.add(stub)
        db.flush()
        session_id = stub.id

    return task.id, session_id


def tick_automations(
    db: Session,
    *,
    now: datetime | None = None,
) -> AutomationTickOut:
    """Fire due enabled automations. Optional ``now`` is a test clock."""
    clock = _as_utc(now) if now is not None else datetime.now(timezone.utc)

    rows = list(db.scalars(select(Automation).order_by(Automation.id)).all())
    fired_ids: list[int] = []
    task_ids: list[int] = []
    session_ids: list[int] = []

    for row in rows:
        if not is_due(row, clock):
            continue

        action = _parse_action(row.action_json)
        action_type = action.get("type", "create_task")
        if action_type != "create_task":
            # Unknown action: skip without updating last_fired_at
            continue

        task_id, session_id = _fire_create_task(db, row, action)
        row.last_fired_at = clock
        fired_ids.append(row.id)
        task_ids.append(task_id)
        if session_id is not None:
            session_ids.append(session_id)

    db.commit()
    return AutomationTickOut(
        now=clock,
        fired_automation_ids=fired_ids,
        task_ids=task_ids,
        session_ids=session_ids,
        fired_count=len(fired_ids),
    )
