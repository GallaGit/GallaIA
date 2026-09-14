"""Phase 4 Goals: CRUD + approve + spawn gate + orchestrator stub + safety rails."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.models import Agent, AgentSession, Project, Task
from app.models.goal import DEFAULT_STUCK_THRESHOLD, GOAL_STATUSES, Goal
from app.schemas.goal import GoalCreate, GoalOrchestrateOut, GoalOut, GoalSpawnOut

SPAWNABLE_STATUSES = frozenset({"approved", "active"})
ORCHESTRATABLE_STATUSES = frozenset({"active"})
TERMINAL_SESSION_STATUSES = frozenset({"completed", "failed", "cancelled", "stuck"})
OPEN_SESSION_STATUSES = frozenset({"queued", "starting", "running", "waiting-inbox"})
# Stub cost per specialist session (accrued on spawn / orchestrate spawn)
STUB_SESSION_COST = 1.0


def goal_out(row: Goal) -> GoalOut:
    return GoalOut(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        status=row.status,
        dod_items=row.get_dod_items(),
        dod_checked=row.get_dod_checked(),
        spend_cap=row.spend_cap,
        spend_accrued=float(row.spend_accrued or 0.0),
        max_wall_seconds=row.max_wall_seconds,
        stuck_threshold=row.stuck_threshold,
        activated_at=row.activated_at,
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


def _pick_agent(db: Session) -> Agent:
    agent = db.scalar(select(Agent).where(Agent.name == "default"))
    if agent is None:
        agent = db.scalar(select(Agent).order_by(Agent.id).limit(1))
    if agent is None:
        raise BadRequestError("No agent available to spawn goal session stub")
    return agent


def _assert_spend_allows(row: Goal, *, action: str) -> None:
    """Reject when spend_cap is 0.00 or accrued has reached/exceeded the cap."""
    if row.spend_cap is None:
        return
    cap = float(row.spend_cap)
    accrued = float(row.spend_accrued or 0.0)
    if cap <= 0.0:
        raise ForbiddenError(
            f"Goal {row.id} spend_cap={cap:.2f} rejects further {action}"
        )
    if accrued >= cap:
        raise ForbiddenError(
            f"Goal {row.id} spend_accrued={accrued:.2f} reached spend_cap={cap:.2f}; "
            f"rejects further {action}"
        )


def _assert_wall_allows(row: Goal, *, action: str) -> None:
    if row.max_wall_seconds is None or row.activated_at is None:
        return
    started = row.activated_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    if elapsed > float(row.max_wall_seconds):
        raise BadRequestError(
            f"Goal {row.id} max_wall_seconds={row.max_wall_seconds} exceeded "
            f"(elapsed={int(elapsed)}s); rejects further {action}"
        )


def _assert_rails(row: Goal, *, action: str) -> None:
    _assert_spend_allows(row, action=action)
    _assert_wall_allows(row, action=action)


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
    threshold = payload.stuck_threshold or DEFAULT_STUCK_THRESHOLD
    row = Goal(
        project_id=project.id,
        name=payload.name.strip(),
        status="draft",
        spend_cap=payload.spend_cap,
        spend_accrued=0.0,
        max_wall_seconds=payload.max_wall_seconds,
        stuck_threshold=threshold,
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


def _create_specialist_session(
    db: Session,
    row: Goal,
    *,
    dod_index: int | None,
    runner: str,
) -> tuple[AgentSession, Task]:
    agent = _pick_agent(db)
    items = row.get_dod_items()
    if dod_index is not None and 0 <= dod_index < len(items):
        label = items[dod_index]
        task_name = f"[goal:{row.id}][{dod_index}] {label}"
        summary = f"specialist stub for goal {row.id} DoD[{dod_index}]: {label}"
    else:
        task_name = f"[goal:{row.id}] {row.name}"
        summary = f"spawn stub for goal {row.id}"

    task = Task(
        project_id=row.project_id,
        name=task_name,
        description=f"Placeholder task for goal {row.id} ({runner})",
        status="todo",
        assignee_agent_id=agent.id,
    )
    db.add(task)
    db.flush()

    stub = AgentSession(
        agent_id=agent.id,
        task_id=task.id,
        goal_id=row.id,
        runner=runner,
        status="queued",
        summary=summary,
        tool_call_log="[]",
    )
    db.add(stub)
    row.spend_accrued = float(row.spend_accrued or 0.0) + STUB_SESSION_COST
    return stub, task


def spawn_goal(db: Session, goal_id: int) -> GoalSpawnOut:
    """Stub spawn: refuse until approved; create first specialist session (+ task link)."""
    row = get_goal(db, goal_id)
    if row.status not in SPAWNABLE_STATUSES:
        raise BadRequestError(
            f"Goal {goal_id} is not approved (status={row.status!r}); "
            "human must approve Definition of Done before spawn"
        )

    _assert_rails(row, action="spawn")

    # First unchecked DoD index (usually 0 on initial spawn)
    checked = row.get_dod_checked()
    next_idx = next((i for i, c in enumerate(checked) if not c), 0)

    stub, task = _create_specialist_session(
        db, row, dod_index=next_idx, runner="goal-spawn"
    )

    if row.status == "approved":
        row.status = "active"
        row.activated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(stub)
    db.refresh(row)

    return GoalSpawnOut(
        goal_id=row.id,
        goal_status=row.status,
        session_id=stub.id,
        task_id=task.id,
    )


def _sessions_for_goal(db: Session, goal_id: int) -> list[AgentSession]:
    stmt = (
        select(AgentSession)
        .where(AgentSession.goal_id == goal_id)
        .order_by(AgentSession.id.asc())
    )
    return list(db.scalars(stmt).all())


def _detect_stuck(row: Goal, sessions: list[AgentSession]) -> bool:
    """True when last N session summaries are identical (non-empty)."""
    n = int(row.stuck_threshold or DEFAULT_STUCK_THRESHOLD)
    if n < 2 or len(sessions) < n:
        return False
    recent = sessions[-n:]
    summaries = [(s.summary or "").strip() for s in recent]
    if not summaries[0]:
        return False
    return all(s == summaries[0] for s in summaries)


def _complete_open_session(
    sessions: list[AgentSession],
    *,
    dod_item: str,
    dod_index: int,
) -> AgentSession | None:
    """Mark the newest open session completed with a DoD-tied stub summary."""
    open_ones = [s for s in sessions if s.status in OPEN_SESSION_STATUSES]
    if not open_ones:
        return None
    current = open_ones[-1]
    current.status = "completed"
    current.summary = f"completed specialist stub DoD[{dod_index}]: {dod_item}"
    current.ended_at = datetime.now(timezone.utc)
    return current


def orchestrate_goal(db: Session, goal_id: int) -> GoalOrchestrateOut:
    """Advance one orchestrator step after a session (stub).

    1. Rails: spend_cap / max_wall_seconds must allow continuation.
    2. Stuck: last N identical summaries → status stuck.
    3. Complete open session (if any) and check off next DoD item.
    4. If all DoD checked → done; else spawn next specialist stub.
    """
    row = get_goal(db, goal_id)
    if row.status == "done":
        return GoalOrchestrateOut(
            goal_id=row.id,
            goal_status=row.status,
            action="noop",
            dod_checked=row.get_dod_checked(),
            detail="goal already done",
        )
    if row.status == "stuck":
        return GoalOrchestrateOut(
            goal_id=row.id,
            goal_status=row.status,
            action="stuck",
            dod_checked=row.get_dod_checked(),
            detail="goal already stuck",
        )
    if row.status not in ORCHESTRATABLE_STATUSES:
        raise BadRequestError(
            f"Goal {goal_id} cannot orchestrate from status {row.status!r} "
            f"(expected active)"
        )

    _assert_rails(row, action="orchestrate")

    sessions = _sessions_for_goal(db, goal_id)
    if _detect_stuck(row, sessions):
        row.status = "stuck"
        db.commit()
        db.refresh(row)
        return GoalOrchestrateOut(
            goal_id=row.id,
            goal_status=row.status,
            action="stuck",
            dod_checked=row.get_dod_checked(),
            detail=(
                f"last {row.stuck_threshold} session summaries identical; "
                "stopped as stuck"
            ),
        )

    items = row.get_dod_items()
    checked = row.get_dod_checked()
    next_idx = next((i for i, c in enumerate(checked) if not c), None)

    if next_idx is None:
        row.status = "done"
        db.commit()
        db.refresh(row)
        return GoalOrchestrateOut(
            goal_id=row.id,
            goal_status=row.status,
            action="done",
            dod_checked=checked,
            detail="all DoD items already checked",
        )

    # Complete current open session against this DoD item (stub)
    _complete_open_session(sessions, dod_item=items[next_idx], dod_index=next_idx)
    checked[next_idx] = True
    row.set_dod_checked(checked)

    if all(checked):
        row.status = "done"
        db.commit()
        db.refresh(row)
        return GoalOrchestrateOut(
            goal_id=row.id,
            goal_status=row.status,
            action="done",
            dod_checked=checked,
            detail=f"checked DoD[{next_idx}]; all DoD complete",
        )

    # Spawn next specialist for the following unchecked item
    following = next((i for i, c in enumerate(checked) if not c), None)
    stub, task = _create_specialist_session(
        db, row, dod_index=following, runner="goal-orchestrate"
    )
    # Re-check spend after accruing spawn cost (cap may now be reached — still
    # allow this spawn that was authorized at step start; next call will 403).
    db.commit()
    db.refresh(stub)
    db.refresh(row)

    # Stuck check including the new session (identical summaries)
    sessions = _sessions_for_goal(db, goal_id)
    if _detect_stuck(row, sessions):
        row.status = "stuck"
        db.commit()
        db.refresh(row)
        return GoalOrchestrateOut(
            goal_id=row.id,
            goal_status=row.status,
            action="stuck",
            session_id=stub.id,
            task_id=task.id,
            dod_checked=row.get_dod_checked(),
            detail=(
                f"spawned session {stub.id} but last {row.stuck_threshold} "
                "summaries identical; stopped as stuck"
            ),
        )

    return GoalOrchestrateOut(
        goal_id=row.id,
        goal_status=row.status,
        action="spawned",
        session_id=stub.id,
        task_id=task.id,
        dod_checked=row.get_dod_checked(),
        detail=f"checked DoD[{next_idx}]; spawned next specialist for DoD[{following}]",
    )
