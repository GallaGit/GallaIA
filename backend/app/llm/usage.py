"""F2.1b — persist gateway `UsageRecord`s into the `llm_usage` table.

The sink only `db.add`s rows on the caller's session (no own commit): SQLite
allows one writer, so rows are committed together with the caller's work.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.llm.gateway import UsageRecord, UsageSink
from app.models.llm_usage import LLMUsage


def db_usage_sink(
    db: Session,
    *,
    source: str,
    agent: str | None = None,
    session_id: int | None = None,
    thread_id: int | None = None,
) -> UsageSink:
    def _sink(record: UsageRecord) -> None:
        db.add(
            LLMUsage(
                source=source,
                agent=agent,
                provider=record.provider,
                model=record.model[:200],
                backend=record.backend,
                ok=record.ok,
                error=(record.error or None) and record.error[:300],
                input_tokens=record.input_tokens,
                output_tokens=record.output_tokens,
                latency_ms=record.latency_ms,
                cost_usd=record.cost_usd,
                session_id=session_id,
                thread_id=thread_id,
            )
        )

    return _sink


def usage_out(row: LLMUsage) -> dict[str, Any]:
    return {
        "id": row.id,
        "created_at": row.created_at,
        "source": row.source,
        "agent": row.agent,
        "provider": row.provider,
        "model": row.model,
        "backend": row.backend,
        "ok": row.ok,
        "error": row.error,
        "input_tokens": row.input_tokens,
        "output_tokens": row.output_tokens,
        "latency_ms": row.latency_ms,
        "cost_usd": row.cost_usd,
        "session_id": row.session_id,
        "thread_id": row.thread_id,
    }


def list_usage(db: Session, *, limit: int = 50) -> list[LLMUsage]:
    return list(
        db.scalars(select(LLMUsage).order_by(LLMUsage.id.desc()).limit(limit)).all()
    )


def usage_summary(db: Session) -> list[dict[str, Any]]:
    """Totals grouped by provider + model."""
    rows = db.execute(
        select(
            LLMUsage.provider,
            LLMUsage.model,
            func.count(LLMUsage.id),
            func.sum(case((LLMUsage.ok.is_(True), 1), else_=0)),
            func.sum(LLMUsage.input_tokens),
            func.sum(LLMUsage.output_tokens),
            func.avg(LLMUsage.latency_ms),
            func.sum(LLMUsage.cost_usd),
        )
        .group_by(LLMUsage.provider, LLMUsage.model)
        .order_by(func.count(LLMUsage.id).desc())
    ).all()
    return [
        {
            "provider": provider,
            "model": model,
            "calls": int(calls or 0),
            "ok_calls": int(ok_calls or 0),
            "input_tokens": int(tin) if tin is not None else None,
            "output_tokens": int(tout) if tout is not None else None,
            "avg_latency_ms": round(float(lat), 1) if lat is not None else None,
            "cost_usd": float(cost) if cost is not None else None,
        }
        for provider, model, calls, ok_calls, tin, tout, lat, cost in rows
    ]
