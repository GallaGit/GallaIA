from fastapi import APIRouter

from app.api.dependencies.db import DbSession
from app.schemas.goal import GoalCreate, GoalOut, GoalSpawnOut
from app.services.goals import (
    approve_goal,
    create_goal,
    get_goal,
    goal_out,
    list_goals,
    spawn_goal,
)

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("", response_model=list[GoalOut])
def api_list_goals(db: DbSession, project_id: int | None = None):
    return [goal_out(g) for g in list_goals(db, project_id=project_id)]


@router.get("/{goal_id}", response_model=GoalOut)
def api_get_goal(goal_id: int, db: DbSession):
    return goal_out(get_goal(db, goal_id))


@router.post("", response_model=GoalOut, status_code=201)
def api_create_goal(payload: GoalCreate, db: DbSession):
    return goal_out(create_goal(db, payload))


@router.post("/{goal_id}/approve", response_model=GoalOut)
def api_approve_goal(goal_id: int, db: DbSession):
    """Human approve: draft -> approved. Required before spawn."""
    return goal_out(approve_goal(db, goal_id))


@router.post("/{goal_id}/spawn", response_model=GoalSpawnOut, status_code=201)
def api_spawn_goal(goal_id: int, db: DbSession):
    """Stub spawn. Returns 400 if goal is not approved (or already active)."""
    return spawn_goal(db, goal_id)
