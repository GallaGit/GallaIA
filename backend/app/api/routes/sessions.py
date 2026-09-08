from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies.db import DbSession
from app.exceptions import NotFoundError
from app.models import AgentSession
from app.schemas import SessionOut

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionOut])
def list_sessions(db: DbSession, task_id: int | None = None, agent_id: int | None = None):
    stmt = select(AgentSession).order_by(AgentSession.id.desc())
    if task_id is not None:
        stmt = stmt.where(AgentSession.task_id == task_id)
    if agent_id is not None:
        stmt = stmt.where(AgentSession.agent_id == agent_id)
    return list(db.scalars(stmt).all())


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: DbSession):
    session = db.get(AgentSession, session_id)
    if session is None:
        raise NotFoundError(f"Session {session_id} not found")
    return session
