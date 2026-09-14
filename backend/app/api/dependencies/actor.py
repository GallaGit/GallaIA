"""Request actor from lean X-Actor-Type / X-Agent-Id headers."""

from typing import Annotated

from fastapi import Depends, Header

from app.core.security import Actor, parse_actor_headers


def get_actor(
    x_actor_type: str | None = Header(default=None, alias="X-Actor-Type"),
    x_agent_id: str | None = Header(default=None, alias="X-Agent-Id"),
) -> Actor:
    return parse_actor_headers(x_actor_type, x_agent_id)


ActorDep = Annotated[Actor, Depends(get_actor)]
