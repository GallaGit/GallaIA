"""Phase 7 Activity feed — append, list, and SSE fan-out stub.

Append-only log persisted in SQLite. An in-process hub notifies SSE
subscribers when a new event is committed (single-process / test-friendly).
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity import ActivityEvent
from app.schemas.activity import ActivityEventCreate, ActivityEventOut

# In-process subscribers (SSE). Cleared on process restart — fine for lean Phase 7.
_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()


def activity_out(row: ActivityEvent) -> ActivityEventOut:
    return ActivityEventOut(
        id=row.id,
        type=row.type,
        message=row.message,
        task_id=row.task_id,
        session_id=row.session_id,
        automation_id=row.automation_id,
        created_at=row.created_at,
    )


def append_activity(
    db: Session,
    *,
    type: str,
    message: str,
    task_id: int | None = None,
    session_id: int | None = None,
    automation_id: int | None = None,
    commit: bool = False,
) -> ActivityEvent:
    """Append one activity row. Caller may own the transaction (commit=False)."""
    row = ActivityEvent(
        type=type.strip()[:80],
        message=message,
        task_id=task_id,
        session_id=session_id,
        automation_id=automation_id,
    )
    db.add(row)
    db.flush()
    if commit:
        db.commit()
        db.refresh(row)
        publish_activity(activity_out(row))
    return row


def create_activity(db: Session, payload: ActivityEventCreate) -> ActivityEvent:
    """HTTP POST helper — always commits and notifies SSE."""
    row = append_activity(
        db,
        type=payload.type,
        message=payload.message,
        task_id=payload.task_id,
        session_id=payload.session_id,
        automation_id=payload.automation_id,
        commit=True,
    )
    return row


def list_activity(db: Session, *, limit: int = 50) -> list[ActivityEvent]:
    lim = max(1, min(limit, 200))
    stmt = (
        select(ActivityEvent)
        .order_by(ActivityEvent.id.desc())
        .limit(lim)
    )
    return list(db.scalars(stmt).all())


def publish_activity(event: ActivityEventOut | dict[str, Any]) -> None:
    """Fan-out to live SSE queues (best-effort; drops if full)."""
    if isinstance(event, ActivityEventOut):
        payload = event.model_dump(mode="json")
    else:
        payload = event
    dead: list[asyncio.Queue[dict[str, Any]]] = []
    for q in list(_subscribers):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            dead.append(q)
        except Exception:  # noqa: BLE001 — never break callers on SSE fan-out
            dead.append(q)
    for q in dead:
        _subscribers.discard(q)


def notify_after_commit(row: ActivityEvent) -> None:
    """Call after db.commit() when append_activity(..., commit=False) was used."""
    publish_activity(activity_out(row))


def subscribe(maxsize: int = 64) -> asyncio.Queue[dict[str, Any]]:
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=maxsize)
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue[dict[str, Any]]) -> None:
    _subscribers.discard(q)


def _sse_pack(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


async def activity_sse_stream(
    *,
    heartbeat_seconds: float = 15.0,
    max_seconds: float | None = None,
) -> AsyncIterator[str]:
    """Yield SSE frames: heartbeat + activity events.

    `max_seconds` ends the stream (useful for TestClient / short demos).
    """
    q = subscribe()
    started = time.monotonic()
    hb = max(0.05, float(heartbeat_seconds))
    try:
        yield _sse_pack(
            "heartbeat",
            {"ok": True, "ts": datetime.now(timezone.utc).isoformat()},
        )
        while True:
            if max_seconds is not None:
                elapsed = time.monotonic() - started
                if elapsed >= max_seconds:
                    yield _sse_pack("end", {"reason": "max_seconds"})
                    break
            try:
                timeout = hb
                if max_seconds is not None:
                    remaining = max_seconds - (time.monotonic() - started)
                    if remaining <= 0:
                        yield _sse_pack("end", {"reason": "max_seconds"})
                        break
                    timeout = min(hb, remaining)
                payload = await asyncio.wait_for(q.get(), timeout=timeout)
                yield _sse_pack("activity", payload)
            except asyncio.TimeoutError:
                yield _sse_pack(
                    "heartbeat",
                    {"ok": True, "ts": datetime.now(timezone.utc).isoformat()},
                )
    finally:
        unsubscribe(q)
