"""Lean schedule-at tick for Phase 3.

Promotes tasks whose ``scheduled_at`` is due (``<= now``) into a runnable
state and optionally creates a session stub. No background daemon — call
``tick_scheduler`` from ``POST /api/v1/scheduler/tick`` (demo / tests).

Full cron string automations are Phase 5 Triggers.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentSession, Task


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def set_task_schedule(db: Session, task: Task, scheduled_at: datetime | None) -> Task:
    """Set or clear ``scheduled_at`` on a task (null clears)."""
    task.scheduled_at = _as_utc(scheduled_at) if scheduled_at is not None else None
    db.commit()
    db.refresh(task)
    return task


def tick_scheduler(
    db: Session,
    *,
    now: datetime | None = None,
) -> dict:
    """Promote due scheduled tasks.

    For each task with ``scheduled_at <= now``:
    - clear ``scheduled_at`` (so it will not re-fire)
    - leave status as ``todo`` if still todo (now runnable for manual /run)
    - if ``assignee_agent_id`` is set, create a minimal session stub
      (``runner=scheduler``, ``status=queued``) — no full mock run

    Returns a small report dict for the API / tests.
    """
    clock = _as_utc(now) if now is not None else datetime.now(timezone.utc)

    # Pull candidates with a schedule; filter due in Python so naive/aware
    # SQLite storage does not break comparisons.
    candidates = list(
        db.scalars(select(Task).where(Task.scheduled_at.is_not(None)).order_by(Task.id)).all()
    )

    promoted_task_ids: list[int] = []
    session_ids: list[int] = []

    for task in candidates:
        due_at = _as_utc(task.scheduled_at)  # type: ignore[arg-type]
        if due_at > clock:
            continue

        task.scheduled_at = None
        promoted_task_ids.append(task.id)

        if task.assignee_agent_id is not None:
            stub = AgentSession(
                agent_id=task.assignee_agent_id,
                task_id=task.id,
                runner="scheduler",
                status="queued",
                summary="promoted by scheduler tick",
                tool_call_log="[]",
            )
            db.add(stub)
            db.flush()
            session_ids.append(stub.id)

    db.commit()
    return {
        "now": clock,
        "promoted_task_ids": promoted_task_ids,
        "session_ids": session_ids,
        "promoted_count": len(promoted_task_ids),
    }
