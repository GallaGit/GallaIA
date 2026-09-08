"""Create tables and seed MVP data."""

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Agent, AgentSession, InboxMessage, Project, Task  # noqa: F401
from app.services.seed import seed_if_empty


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
