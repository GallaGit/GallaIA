"""Phase 7 live session viewer — SSE over status + tool-call log.

Polls SQLite for session status and tool_call_log growth. Replays existing
log lines first, then emits deltas + heartbeats. Single-process / test-friendly.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from sqlalchemy.orm import Session, sessionmaker

from app.models import AgentSession


def _sse_pack(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _read_session(
    session_factory: sessionmaker[Session], session_id: int
) -> dict[str, Any] | None:
    """Load a plain snapshot inside a short-lived DB session (no detached ORM)."""
    with session_factory() as db:
        row = db.get(AgentSession, session_id)
        if row is None:
            return None
        tools = list(row.get_tool_events())
        return {
            "session_id": row.id,
            "status": row.status,
            "runner": row.runner,
            "summary": row.summary,
            "tool_events": tools,
            "tool_count": len(tools),
            "started_at": row.started_at,
            "ended_at": row.ended_at,
        }


def _status_payload(snap: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": snap["session_id"],
        "status": snap["status"],
        "runner": snap["runner"],
        "summary": snap["summary"],
        "tool_count": snap["tool_count"],
        "started_at": snap["started_at"],
        "ended_at": snap["ended_at"],
    }


async def session_sse_stream(
    *,
    session_factory: sessionmaker[Session],
    session_id: int,
    poll_seconds: float = 0.25,
    heartbeat_seconds: float = 15.0,
    max_seconds: float | None = None,
) -> AsyncIterator[str]:
    """Yield SSE: status snapshot, tool-log lines (replay + live), heartbeats.

    Opens short-lived DB sessions per poll so the stream does not hold one
    connection forever. Ends with event:end when max_seconds elapses.
    """
    started = time.monotonic()
    hb = max(0.05, float(heartbeat_seconds))
    poll = max(0.05, float(poll_seconds))
    sent_tool_count = 0
    last_status: str | None = None
    last_runner: str | None = None

    snap = await asyncio.to_thread(_read_session, session_factory, session_id)
    if snap is None:
        yield _sse_pack("error", {"message": f"Session {session_id} not found"})
        yield _sse_pack("end", {"reason": "not_found"})
        return

    last_status = snap["status"]
    last_runner = snap["runner"]
    yield _sse_pack("status", _status_payload(snap))

    for i, ev in enumerate(snap["tool_events"]):
        yield _sse_pack(
            "tool",
            {"session_id": session_id, "index": i, "event": ev},
        )
        sent_tool_count = i + 1

    yield _sse_pack(
        "heartbeat",
        {"ok": True, "ts": datetime.now(timezone.utc).isoformat()},
    )

    next_hb = time.monotonic() + hb
    while True:
        if max_seconds is not None:
            elapsed = time.monotonic() - started
            if elapsed >= max_seconds:
                yield _sse_pack("end", {"reason": "max_seconds"})
                break

        sleep_for = poll
        if max_seconds is not None:
            remaining = max_seconds - (time.monotonic() - started)
            if remaining <= 0:
                yield _sse_pack("end", {"reason": "max_seconds"})
                break
            sleep_for = min(poll, remaining)

        await asyncio.sleep(sleep_for)

        snap = await asyncio.to_thread(_read_session, session_factory, session_id)
        if snap is None:
            yield _sse_pack("error", {"message": f"Session {session_id} disappeared"})
            yield _sse_pack("end", {"reason": "not_found"})
            break

        events = snap["tool_events"]
        while sent_tool_count < len(events):
            ev = events[sent_tool_count]
            yield _sse_pack(
                "tool",
                {
                    "session_id": session_id,
                    "index": sent_tool_count,
                    "event": ev,
                },
            )
            sent_tool_count += 1

        if snap["status"] != last_status or snap["runner"] != last_runner:
            last_status = snap["status"]
            last_runner = snap["runner"]
            yield _sse_pack("status", _status_payload(snap))

        now = time.monotonic()
        if now >= next_hb:
            yield _sse_pack(
                "heartbeat",
                {"ok": True, "ts": datetime.now(timezone.utc).isoformat()},
            )
            next_hb = now + hb
