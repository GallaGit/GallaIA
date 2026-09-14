"""Phase 4 Goals foundation: CRUD + human approve + spawn gate stub.

Full orchestrator loop and spend/time/stuck rails are later slices.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError, NotFoundError
from app.models import Agent, AgentSession, Project, Task
from app.models.goal import GOAL_STATUSES, Goal
from app.schemas.goal import GoalCreate, GoalOut, GoalSpawnOut

SPAWNABLE_STATUSES = frozenset({"approved", "active"})


def goal_out(row: Goal) -> GoalOut:
    return GoalOut(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        status=row.status,
        dod_items=row.get_dod_items(),
        approved_at=row.approved_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _default_project(db: Session) -> Project:
    project = db.scalar(select(Project).where(Project.slug == "default"))
    if project is None:
        raise BadRequestError("Default project not found; seed required")
    return project


def _resolve_project(db: Session, project_id: int | None) -> Project:
    if project_id is None:
        return _default_project(db)
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundError(f"Project {project_id} not found")
    return project


def list_goals(db: Session, *, project_id: int | None = None) -> list[Goal]:
    stmt = select(Goal).order_by(Goal.id.desc())
    if project_id is not None:
        stmt = stmt.where(Goal.project_id == project_id)
    return list(db.scalars(stmt).all())


def get_goal(db: Session, goal_id: int) -> Goal:
    row = db.get(Goal, goal_id)
    if row is None:
        raise NotFoundError(f"Goal {goal_id} not found")
    return row


def create_goal(db: Session, payload: GoalCreate) -> Goal:
    items = [s.strip() for s in payload.dod_items if str(s).strip()]
    if not items:
        raise BadRequestError("dod_items must contain at least one non-empty string")

    project = _resolve_project(db, payload.project_id)
    row = Goal(
        project_id=project.id,
        name=payload.name.strip(),
        status="draft",
    )
    row.set_dod_items(items)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def approve_goal(db: Session, goal_id: int) -> Goal:
    """Human gate: draft -> approved. Idempotent if already approved."""
    row = get_goal(db, goal_id)
    if row.status == "approved":
        return row
    if row.status != "draft":
        raise BadRequestError(
            f"Goal {goal_id} cannot be approved from status {row.status!r} "
            f"(expected draft); allowed statuses: {GOAL_STATUSES}"
        )
    row.status = "approved"
    row.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def spawn_goal(db: Session, goal_id: int) -> GoalSpawnOut:
    """Stub spawn: refuse until approved; create placeholder session (+ task link).

    Real orchestrator (next specialist after each session) is a later Phase 4 slice.
    """
    row = get_goal(db, goal_id)
    if row.status not in SPAWNABLE_STATUSES:
        raise BadRequestError(
            f"Goal {goal_id} is not approved (status={row.status!r}); "
            "human must approve Definition of Done before spawn"
        )

    agent = db.scalar(select(Agent).where(Agent.name == "default"))
    if agent is None:
        agent = db.scalar(select(Agent).order_by(Agent.id).limit(1))
    if agent is None:
        raise BadRequestError("No agent available to spawn goal session stub")

    task = Task(
        project_id=row.project_id,
        name=f"[goal:{row.id}] {row.name}",
        description=f"Placeholder task for goal {row.id} spawn stub",
        status="todo",
        assignee_agent_id=agent.id,
    )
    db.add(task)
    db.flush()

    stub = AgentSession(
        agent_id=agent.id,
        task_id=task.id,
        goal_id=row.id,
        runner="goal-spawn",
        status="queued",
        summary=f"spawn stub for goal {row.id} (orchestrator not yet built)",
        tool_call_log="[]",
    )
    db.add(stub)

    if row.status == "approved":
        row.status = "active"

    db.commit()
    db.refresh(stub)
    db.refresh(row)

    return GoalSpawnOut(
        goal_id=row.id,
        goal_status=row.status,
        session_id=stub.id,
        task_id=task.id,
    )
