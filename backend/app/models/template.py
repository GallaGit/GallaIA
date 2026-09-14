from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TaskTemplate(Base):
    """Reusable recipe that instantiates an ordered chain of task cards."""

    __tablename__ = "task_templates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project = relationship("Project", back_populates="templates")
    steps = relationship(
        "TaskTemplateStep",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TaskTemplateStep.position",
    )
    tasks = relationship("Task", back_populates="template")


class TaskTemplateStep(Base):
    """One ordered step in a TaskTemplate."""

    __tablename__ = "task_template_steps"
    __table_args__ = (
        UniqueConstraint("template_id", "position", name="uq_template_step_pos"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("task_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_agent_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    approval_gate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_previous_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    template = relationship("TaskTemplate", back_populates="steps")
