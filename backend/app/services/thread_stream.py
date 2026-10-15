"""F1.4 — Live SSE stream of thread messages (backend only).

Replays the thread's existing messages, then runs `advance_thread` step by
step with the deterministic mock LLM (no API key needed) and emits every
newly saved message (plan, delegations, results, summary) as a `message`
SSE event as soon as it is committed. Ends with an `end` event.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.exceptions import ConflictError
from app.models import Message, Thread
from app.schemas import MessageOut
from app.services.thread_agents import advance_thread, mock_llm


def _sse_pack(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _read_snapshot(
    session_factory: sessionmaker[Session], thread_id: int
) -> tuple[str, list[dict[str, Any]]] | None:
    """Load thread status + messages as plain dicts (no detached ORM)."""
    with session_factory() as db:
        thread = db.get(Thread, thread_id)
        if thread is None:
            return None
        rows = list(
            db.scalars(
                select(Message)
                .where(Message.thread_id == thread_id)
                .order_by(Message.created_at, Message.id)
            ).all()
        )
        messages = [
            MessageOut.model_validate(m).model_dump(mode="json") for m in rows
        ]
        return thread.status, messages


def _advance_one_step(
    session_factory: sessionmaker[Session], thread_id: int
) -> list[dict[str, Any]]:
    """Run a single advance step with the mock LLM; return created messages.

    Raises:
        LookupError: thread no longer exists.
        ConflictError: thread was closed mid-stream.
    """
    with session_factory() as db:
        thread = db.get(Thread, thread_id)
        if thread is None:
            raise LookupError(f"Thread {thread_id} not found")
        created = advance_thread(db, thread, max_steps=1, llm=mock_llm)
        return [
            MessageOut.model_validate(m).model_dump(mode="json") for m in created
        ]


async def thread_sse_stream(
    *,
    session_factory: sessionmaker[Session],
    thread_id: int,
    max_steps: int = 6,
    heartbeat_seconds: float = 15.0,
    max_seconds: float | None = None,
) -> AsyncIterator[str]:
    """Yield SSE: replayed `message` events, live `message` events, `end`.

    Opens short-lived DB sessions per step so the stream never holds one
    connection. `max_seconds` ends the stream early (tests / short demos).
    """
    started = time.monotonic()
    hb = max(0.05, float(heartbeat_seconds))
    max_steps = max(1, int(max_steps))

    def _expired() -> bool:
        return max_seconds is not None and (time.monotonic() - started) >= max_seconds

    snap = await asyncio.to_thread(_read_snapshot, session_factory, thread_id)
    if snap is None:
        yield _sse_pack("error", {"message": f"Thread {thread_id} not found"})
        yield _sse_pack("end", {"reason": "not_found"})
        return
    _status, existing = snap

    for msg in existing:
        yield _sse_pack("message", msg)

    yield _sse_pack(
        "heartbeat",
        {"ok": True, "ts": datetime.now(timezone.utc).isoformat()},
    )

    created_total = 0
    steps = 0
    while steps < max_steps:
        if _expired():
            yield _sse_pack("end", {"reason": "max_seconds"})
            return
        try:
            created = await asyncio.to_thread(
                _advance_one_step, session_factory, thread_id
            )
        except LookupError:
            yield _sse_pack("error", {"message": f"Thread {thread_id} disappeared"})
            yield _sse_pack("end", {"reason": "not_found"})
            return
        except ConflictError:
            yield _sse_pack("error", {"message": f"Thread {thread_id} is closed"})
            yield _sse_pack("end", {"reason": "closed"})
            return
        steps += 1
        if not created:
            break
        for msg in created:
            yield _sse_pack("message", msg)
            created_total += 1

    yield _sse_pack(
        "heartbeat",
        {"ok": True, "ts": datetime.now(timezone.utc).isoformat()},
    )
    yield _sse_pack("end", {"reason": "done", "created": created_total})
