"""F2.1b — one row per LLM gateway attempt (provider, model, tokens, latency)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LLMUsage(Base):
    """Append-only usage log. Never stores prompts, responses or API keys."""

    __tablename__ = "llm_usage"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    # Where the call came from: "thread" (F1.2 agents) | "session" (task runner).
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="", index=True)
    agent: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    backend: Mapped[str] = mapped_column(String(20), nullable=False, default="http")
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    session_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thread_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
