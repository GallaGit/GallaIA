from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies.db import DbSession
from app.exceptions import NotFoundError
from app.models import Agent
from app.schemas import (
    AgentFsOut,
    AgentFsUpdate,
    AgentGrantsOut,
    AgentGrantsUpdate,
    AgentNetworkOut,
    AgentNetworkUpdate,
    AgentOut,
)
from app.services.filesystem import fs_out, replace_agent_fs
from app.services.grants import grants_out, replace_agent_grants, require_agent
from app.services.network import network_out, replace_agent_network

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentOut])
def list_agents(db: DbSession, project_id: int | None = None):
    stmt = select(Agent).order_by(Agent.id)
    if project_id is not None:
        stmt = stmt.where(Agent.project_id == project_id)
    return list(db.scalars(stmt).all())


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: int, db: DbSession):
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise NotFoundError(f"Agent {agent_id} not found")
    return agent


@router.get("/{agent_id}/grants", response_model=AgentGrantsOut)
def get_agent_grants(agent_id: int, db: DbSession) -> AgentGrantsOut:
    return grants_out(require_agent(db, agent_id))


@router.put("/{agent_id}/grants", response_model=AgentGrantsOut)
def put_agent_grants(
    agent_id: int, payload: AgentGrantsUpdate, db: DbSession
) -> AgentGrantsOut:
    agent = require_agent(db, agent_id)
    return replace_agent_grants(db, agent, payload.grants)


@router.get("/{agent_id}/network", response_model=AgentNetworkOut)
def get_agent_network(agent_id: int, db: DbSession) -> AgentNetworkOut:
    return network_out(require_agent(db, agent_id))


@router.put("/{agent_id}/network", response_model=AgentNetworkOut)
def put_agent_network(
    agent_id: int, payload: AgentNetworkUpdate, db: DbSession
) -> AgentNetworkOut:
    agent = require_agent(db, agent_id)
    return replace_agent_network(db, agent, payload.mode, payload.allowlist)


@router.get("/{agent_id}/fs", response_model=AgentFsOut)
def get_agent_fs(agent_id: int, db: DbSession) -> AgentFsOut:
    return fs_out(require_agent(db, agent_id))


@router.put("/{agent_id}/fs", response_model=AgentFsOut)
def put_agent_fs(agent_id: int, payload: AgentFsUpdate, db: DbSession) -> AgentFsOut:
    agent = require_agent(db, agent_id)
    return replace_agent_fs(db, agent, payload.roots)
