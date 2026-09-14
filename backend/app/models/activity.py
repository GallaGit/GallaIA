"""Phase 7 Activity feed — append-only global event log."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ActivityEvent(Base):
    """Append-only activity row for the global feed / SSE stub.

    `type` is a short dotted kind (e.g. task.created, webhook.received,
    automation.fired). Optional FK refs link back to task/session/automation.
    """

    __tablename__ = "activity_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    task_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, default=None
    )
    session_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, default=None
    )
    automation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("automations.id", ondelete="SET NULL"), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
