import json
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

GOAL_STATUSES = ("draft", "approved", "active", "done", "stuck")
DEFAULT_STUCK_THRESHOLD = 19


class Goal(Base):
    """Phase 4 Goals: DoD gate + orchestrator stub + spend/time/stuck rails."""

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # draft | approved | active | done | stuck
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    # JSON list of Definition-of-Done checkbox strings
    dod_items_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # JSON list of bools parallel to dod_items (checked-off by orchestrator)
    dod_checked_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # Safety rails (None spend_cap / max_wall_seconds = unlimited)
    spend_cap: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    spend_accrued: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_wall_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    stuck_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_STUCK_THRESHOLD
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
        # Reset / align checked flags to same length (unchecked)
        self.dod_checked_json = json.dumps([False] * len(items))

    def get_dod_checked(self) -> list[bool]:
        items = self.get_dod_items()
        try:
            raw = json.loads(self.dod_checked_json or "[]")
        except json.JSONDecodeError:
            raw = []
        if not isinstance(raw, list):
            raw = []
        flags = [bool(x) for x in raw]
        # Pad / trim to match current DoD length
        if len(flags) < len(items):
            flags.extend([False] * (len(items) - len(flags)))
        return flags[: len(items)]

    def set_dod_checked(self, flags: list[bool]) -> None:
        items = self.get_dod_items()
        aligned = [bool(x) for x in flags[: len(items)]]
        if len(aligned) < len(items):
            aligned.extend([False] * (len(items) - len(aligned)))
        self.dod_checked_json = json.dumps(aligned)
