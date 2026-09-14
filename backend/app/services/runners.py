"""Phase 7 local runner routing stub.

`runner_route=mock|local` (settings / env). OS-local binary is future work;
when the intended route is `local`, we record `local-stub` and do not spawn
a process. POST /api/v1/runners/route is the lean control-plane surface.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.exceptions import NotFoundError
from app.models import AgentSession
from app.schemas.runner import RunnerRouteIn, RunnerRouteOut

RouteLiteral = Literal["mock", "local"]

# In-process last route decision (also optional session.runner update).
_last_route: dict[str, Any] = {
    "intended": "mock",
    "effective_runner": "mock",
    "recorded_at": None,
    "session_id": None,
    "note": None,
}


def normalize_route(value: str) -> RouteLiteral:
    v = (value or "mock").strip().lower()
    if v not in ("mock", "local"):
        raise ValueError("runner_route must be 'mock' or 'local'")
    return v  # type: ignore[return-value]


def effective_runner_for(route: RouteLiteral) -> str:
    """Map intended route to session.runner label."""
    if route == "local":
        return "local-stub"
    return "mock"


def current_route_info(settings: Settings) -> dict[str, Any]:
    configured = normalize_route(settings.runner_route)
    return {
        "configured_route": configured,
        "effective_runner": effective_runner_for(configured),
        "local_runner_available": False,
        "note": (
            "OS-local runner binary is future work. "
            "When route=local, sessions use runner=local-stub (no real process)."
        ),
        "last_recorded": dict(_last_route) if _last_route.get("recorded_at") else None,
    }


def record_runner_route(
    db: Session,
    settings: Settings,
    payload: RunnerRouteIn,
) -> RunnerRouteOut:
    """Record intended mock|local route; optionally stamp session.runner.

    Does not launch a local binary. Prefer this over 501 for the record API —
    callers get a clear stub response instead of a hard failure.
    """
    intended = normalize_route(payload.route or settings.runner_route)
    effective = effective_runner_for(intended)
    note = (
        "Recorded mock route."
        if intended == "mock"
        else (
            "OS-local runner not implemented yet; recorded as local-stub. "
            "No local binary was started."
        )
    )

    session_id = payload.session_id
    if session_id is not None:
        row = db.get(AgentSession, session_id)
        if row is None:
            raise NotFoundError(f"Session {session_id} not found")
        row.runner = effective
        db.add(row)
        db.commit()
        db.refresh(row)

    now = datetime.now(timezone.utc)
    _last_route.update(
        {
            "intended": intended,
            "effective_runner": effective,
            "recorded_at": now.isoformat(),
            "session_id": session_id,
            "note": note,
        }
    )

    return RunnerRouteOut(
        intended=intended,
        effective_runner=effective,
        local_runner_available=False,
        session_id=session_id,
        recorded_at=now,
        note=note,
        status="recorded",
    )
