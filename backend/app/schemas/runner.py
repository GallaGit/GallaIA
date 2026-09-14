from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RunnerRouteIn(BaseModel):
    """Record intended runner route without launching a local binary."""

    route: Literal["mock", "local"] = Field(
        description="Intended route: mock (in-process) or local (future OS binary).",
    )
    session_id: int | None = Field(
        default=None,
        description="Optional session to stamp with effective runner label.",
    )


class RunnerRouteOut(BaseModel):
    intended: Literal["mock", "local"]
    effective_runner: str
    local_runner_available: bool = False
    session_id: int | None = None
    recorded_at: datetime
    note: str
    status: str = "recorded"


class RunnerRouteInfoOut(BaseModel):
    configured_route: Literal["mock", "local"]
    effective_runner: str
    local_runner_available: bool = False
    note: str
    last_recorded: dict | None = None
