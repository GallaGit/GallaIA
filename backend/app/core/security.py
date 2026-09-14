"""Lean actor headers for Phase 3 gate authz (not full OAuth).

Convention (MVP, single-operator + agent callers):
  X-Actor-Type: human | agent   (default: human if omitted)
  X-Agent-Id:   <int>           (optional; agent caller id)

UI / curl without headers = human operator.
Agent runtimes / MCP tools SHOULD send X-Actor-Type: agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ActorType = Literal["human", "agent"]


@dataclass(frozen=True)
class Actor:
    """Resolved request actor. Not a security principal — header convention only."""

    type: ActorType
    agent_id: int | None = None

    @property
    def is_agent(self) -> bool:
        return self.type == "agent"

    @property
    def is_human(self) -> bool:
        return self.type == "human"


def parse_actor_headers(
    x_actor_type: str | None = None,
    x_agent_id: str | None = None,
) -> Actor:
    """Parse lean actor headers. Invalid type → BadRequestError."""
    from app.exceptions import BadRequestError

    raw = (x_actor_type or "human").strip().lower()
    if raw not in ("human", "agent"):
        raise BadRequestError(
            f"Invalid X-Actor-Type: {x_actor_type!r} (expected human|agent)"
        )
    agent_id: int | None = None
    if x_agent_id is not None and str(x_agent_id).strip() != "":
        try:
            agent_id = int(str(x_agent_id).strip())
        except ValueError as exc:
            raise BadRequestError(
                f"Invalid X-Agent-Id: {x_agent_id!r} (expected int)"
            ) from exc
    return Actor(type=raw, agent_id=agent_id)  # type: ignore[arg-type]
