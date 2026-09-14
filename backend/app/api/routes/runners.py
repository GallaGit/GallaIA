"""Local runner routing stub (Phase 7 slice 3)."""

from fastapi import APIRouter

from app.api.dependencies.db import DbSession
from app.core.config import get_settings
from app.schemas.runner import RunnerRouteIn, RunnerRouteInfoOut, RunnerRouteOut
from app.services.runners import current_route_info, record_runner_route

router = APIRouter(prefix="/runners", tags=["runners"])


@router.get("/route", response_model=RunnerRouteInfoOut)
def api_get_runner_route():
    """Current configured runner_route + last recorded decision."""
    return current_route_info(get_settings())


@router.post("/route", response_model=RunnerRouteOut)
def api_post_runner_route(payload: RunnerRouteIn, db: DbSession):
    """Record intended mock|local route without launching a local binary.

    When route=local, effective_runner becomes ``local-stub`` (OS-local
    runner is future work). Optional session_id stamps that session's
    runner field.
    """
    return record_runner_route(db, get_settings(), payload)
