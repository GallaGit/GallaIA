import json
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

GOAL_STATUSES = ("draft", "approved", "active", "done")


class Goal(Base):
    """Phase 4 Goals: human-approved Definition of Done before spawn.

    Orchestrator loop and spend/time/stuck rails come in later slices.
    """

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # draft | approved | active | done
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    # JSON list of Definition-of-Done checkbox strings
    dod_items_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    project = relationship("Project", back_populates="goals")
    sessions = relationship("AgentSession", back_populates="goal")

    def get_dod_items(self) -> list[str]:
        try:
            raw = json.loads(self.dod_items_json or "[]")
        except json.JSONDecodeError:
            return []
        if not isinstance(raw, list):
            return []
        return [str(x) for x in raw]

    def set_dod_items(self, items: list[str]) -> None:
        self.dod_items_json = json.dumps(list(items), ensure_ascii=False)
