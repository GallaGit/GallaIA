from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

TASK_STATUSES = ("todo", "doing", "review", "done")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="todo", index=True)
    assignee_agent_id: Mapped[int | None] = mapped_column(
        ForeignKey("agents.id"), nullable=True, index=True
    )
    approval_gate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("task_templates.id"), nullable=True, index=True
    )
    template_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    step_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    depends_on_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project = relationship("Project", back_populates="tasks")
    assignee_agent = relationship("Agent", back_populates="tasks")
    sessions = relationship("AgentSession", back_populates="task", cascade="all, delete-orphan")
    template = relationship("TaskTemplate", back_populates="tasks")
    depends_on = relationship("Task", remote_side=[id], foreign_keys=[depends_on_task_id])
