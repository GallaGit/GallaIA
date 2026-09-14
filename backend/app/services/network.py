"""Load and replace per-agent network policy in SQLite."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agentos.network import (
    NETWORK_MODES,
    NetworkPolicy,
    dump_allowlist_json,
    normalize_allowlist,
    normalize_mode,
    parse_allowlist_json,
)
from app.exceptions import BadRequestError
from app.models import Agent, AgentNetworkPolicy
from app.schemas.network import AgentNetworkOut
from app.services.grants import require_agent, require_agent_by_name

__all__ = [
    "network_policy_for_agent",
    "network_out",
    "replace_agent_network",
    "require_agent",
    "require_agent_by_name",
]


def network_policy_for_agent(agent: Agent | None) -> NetworkPolicy:
    if agent is None or agent.network_policy is None:
        return NetworkPolicy.open()
    row = agent.network_policy
    try:
        return NetworkPolicy.from_parts(row.mode, parse_allowlist_json(row.allowlist_json))
    except ValueError:
        return NetworkPolicy.open()


def network_out(agent: Agent) -> AgentNetworkOut:
    policy = network_policy_for_agent(agent)
    return AgentNetworkOut(
        agent_id=agent.id,
        agent_name=agent.name,
        mode=policy.mode,
        allowlist=list(policy.allowlist),
    )


def replace_agent_network(
    db: Session, agent: Agent, mode: str, allowlist: list[str]
) -> AgentNetworkOut:
    try:
        resolved = normalize_mode(mode)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc
    if resolved not in NETWORK_MODES:
        raise BadRequestError(f"Invalid network mode: {mode}")
    hosts = normalize_allowlist(allowlist)
    payload = dump_allowlist_json(hosts)

    row = agent.network_policy
    if row is None:
        row = AgentNetworkPolicy(
            agent_id=agent.id, mode=resolved, allowlist_json=payload
        )
        db.add(row)
    else:
        row.mode = resolved
        row.allowlist_json = payload
    db.commit()
    db.refresh(agent)
    return network_out(agent)
