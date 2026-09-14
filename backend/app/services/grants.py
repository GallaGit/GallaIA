"""Load and replace per-agent grants in SQLite. Default deny when the list is empty."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agentos.grants import GRANT_KINDS, GrantSet, normalize_grant
from app.exceptions import BadRequestError, NotFoundError
from app.models import Agent, AgentGrant
from app.schemas.grant import AgentGrantsOut, GrantItem


def grant_set_from_rows(rows: list[AgentGrant] | None) -> GrantSet:
    return GrantSet.from_pairs((row.kind, row.name) for row in (rows or []))


def grant_set_for_agent(agent: Agent) -> GrantSet:
    return grant_set_from_rows(list(agent.grants or []))


def load_agent_by_name(db: Session, name: str) -> Agent | None:
    return db.scalar(select(Agent).where(Agent.name == name))


def grants_out(agent: Agent) -> AgentGrantsOut:
    items = GrantSet.from_pairs((g.kind, g.name) for g in agent.grants).as_list()
    return AgentGrantsOut(
        agent_id=agent.id,
        agent_name=agent.name,
        grants=[GrantItem.model_validate(row) for row in items],
    )


def replace_agent_grants(
    db: Session, agent: Agent, items: list[GrantItem]
) -> AgentGrantsOut:
    seen: set[tuple[str, str]] = set()
    normalized: list[tuple[str, str]] = []
    for item in items:
        kind, name = normalize_grant(item.kind, item.name)
        if kind not in GRANT_KINDS:
            raise BadRequestError(f"Invalid grant kind: {item.kind}")
        if not name:
            raise BadRequestError("Grant name is required")
        key = (kind, name)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(key)

    for row in list(agent.grants):
        db.delete(row)
    db.flush()
    for kind, name in normalized:
        db.add(AgentGrant(agent_id=agent.id, kind=kind, name=name))
    db.commit()
    db.refresh(agent)
    return grants_out(agent)


def require_agent(db: Session, agent_id: int) -> Agent:
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise NotFoundError(f"Agent {agent_id} not found")
    return agent


def require_agent_by_name(db: Session, name: str) -> Agent:
    agent = load_agent_by_name(db, name)
    if agent is None:
        raise NotFoundError(f"Unknown agent {name!r}")
    return agent
