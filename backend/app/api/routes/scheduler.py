"""Demo scheduler tick — no background daemon."""

from fastapi import APIRouter

from app.api.dependencies.db import DbSession
from app.schemas.scheduler import SchedulerTickIn, SchedulerTickOut
from app.services.scheduler import tick_scheduler

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.post("/tick", response_model=SchedulerTickOut)
def post_scheduler_tick(db: DbSession, payload: SchedulerTickIn | None = None):
    """Promote due scheduled_at tasks. Optional now for a test clock."""
    body = payload or SchedulerTickIn()
    result = tick_scheduler(db, now=body.now)
    return SchedulerTickOut(**result)
