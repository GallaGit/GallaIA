from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False, default="claude-sonnet-4")
    # RECONSTRUCTED from Danny Postma's AgentOS talk — not his verbatim prompts.
    foundational_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    role_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    runner_preference: Mapped[str] = mapped_column(String(20), nullable=False, default="cloud")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project = relationship("Project", back_populates="agents")
    tasks = relationship("Task", back_populates="assignee_agent")
    sessions = relationship("AgentSession", back_populates="agent")
