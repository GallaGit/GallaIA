import json
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AgentSession(Base):
    """One agent run (ephemeral in real AgentOS; persisted as a record here)."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), nullable=False, index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True, index=True)
    runner: Mapped[str] = mapped_column(String(20), nullable=False, default="mock")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="starting", index=True)
    # JSON array of tool-call events for the live / replay viewer
    tool_call_log: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agent = relationship("Agent", back_populates="sessions")
    task = relationship("Task", back_populates="sessions")

    def get_tool_events(self) -> list:
        try:
            return json.loads(self.tool_call_log or "[]")
        except json.JSONDecodeError:
            return []

    def set_tool_events(self, events: list) -> None:
        self.tool_call_log = json.dumps(events, ensure_ascii=False)
