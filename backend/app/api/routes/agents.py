from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies.db import DbSession
from app.exceptions import NotFoundError
from app.models import Agent
from app.schemas import AgentOut

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
