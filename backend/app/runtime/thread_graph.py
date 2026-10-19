"""F2.2a — optional LangGraph engine for `advance_thread`.

Same result as the classic loop, same messages, same activity events: the
graph only orchestrates the pick/handle cycle, every decision still comes from
`app.services.thread_agents` so both engines cannot drift.

The LangGraph state carries primitives only (ids and counters); the SQLAlchemy
session, the thread, the llm and the event sink travel in
`config["configurable"]`, never in the checkpointed state.

`langgraph` is optional (like litellm): when it is missing, `langgraph_available()`
returns False and `advance_thread` keeps using the classic loop.
"""

from __future__ import annotations

import logging
import os
from typing import Annotated, Any, TypedDict

from sqlalchemy.orm import Session

from app.models import Message, Thread
from app.models.activity import ActivityEvent
from app.services import thread_agents

logger = logging.getLogger(__name__)

CLASSIC = "classic"
LANGGRAPH = "langgraph"

_NODE_PICK = "pick"
_NODE_ORQUESTADOR = "orquestador"
_NODE_SPECIALIST = "specialist"

try:  # pragma: no cover — depends on the optional dependency
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver

    _CHECKPOINTER: Any = MemorySaver()
except Exception:  # noqa: BLE001 — langgraph is optional
    MemorySaver = None  # type: ignore[assignment, misc]
    RunnableConfig = dict  # type: ignore[assignment, misc]
    _CHECKPOINTER = None

_COMPILED: Any = None


def langgraph_available() -> bool:
    """True when the optional `langgraph` package can be imported."""
    try:
        import langgraph.graph  # noqa: F401
    except Exception:  # noqa: BLE001 — any import problem means "not available"
        return False
    return True


def thread_engine() -> str:
    """Selected thread engine: "classic" (default) or "langgraph".

    Unknown values fall back to "classic". The process env is a second chance
    when settings cannot be read (e.g. run outside the app).
    """
    value = ""
    try:
        from app.core.config import get_settings

        value = (getattr(get_settings(), "thread_engine", "") or "").strip()
    except Exception:  # noqa: BLE001 — settings unavailable in isolation
        value = ""
    value = (value or os.getenv("GALLAIA_THREAD_ENGINE") or "").strip().lower()
    return LANGGRAPH if value == LANGGRAPH else CLASSIC


def _last(_current: Any, new: Any) -> Any:
    """Last-write-wins reducer that also accepts None (LastValue drops None)."""
    return new


class ThreadState(TypedDict):
    """Checkpointed state. Primitives only — no ORM objects, no session."""

    thread_id: int
    max_steps: int
    steps: int
    handled: list[int]
    created: list[int]
    pending: Annotated[int | None, _last]


def _configurable(config: Any) -> dict[str, Any]:
    return ((config or {}).get("configurable") or {})


def _pick(state: ThreadState, config: RunnableConfig) -> dict[str, Any]:
    """Next unanswered agent-addressed message id, or None when done."""
    db: Session = _configurable(config)["db"]
    messages = thread_agents._load_messages(db, state["thread_id"])
    pending = thread_agents._next_pending(messages, set(state.get("handled") or []))
    pending_id = pending.id if pending is not None else None
    if int(state.get("steps", 0)) >= int(state["max_steps"]):
        pending_id = None  # step budget spent
    return {"pending": pending_id}


def _route(state: ThreadState, config: RunnableConfig) -> str:
    """END when there is nothing to answer, else the addressed handler."""
    pending = state.get("pending")
    if pending is None:
        return "end"
    db: Session = _configurable(config)["db"]
    messages = thread_agents._load_messages(db, state["thread_id"])
    msg = next((m for m in messages if m.id == pending), None)
    if msg is None:
        return "end"
    return _NODE_ORQUESTADOR if msg.recipient == _NODE_ORQUESTADOR else _NODE_SPECIALIST


def _answer(state: ThreadState, config: RunnableConfig) -> dict[str, Any]:
    """Let the addressed agent answer the pending message and persist it."""
    cfg = _configurable(config)
    db: Session = cfg["db"]
    thread: Thread = cfg["thread"]
    llm = cfg["llm"]
    events: list[ActivityEvent] = cfg["events"]

    pending = state.get("pending")
    messages = thread_agents._load_messages(db, state["thread_id"])
    msg = next((m for m in messages if m.id == pending), None)
    if msg is None:
        return {"pending": None}

    if msg.recipient == _NODE_ORQUESTADOR:
        replies = thread_agents._handle_orquestador(thread, msg, messages, llm)
    else:
        replies = thread_agents._handle_specialist(thread, msg, llm)

    if not replies:  # undefined pair → handled implicitly, no reply, no step
        handled = set(state.get("handled") or [])
        handled.add(msg.id)
        return {"handled": sorted(handled), "pending": None}

    created = list(state.get("created") or [])
    for reply in replies:
        events.append(thread_agents._persist_reply(db, thread, reply))
        created.append(reply.id)
    steps = int(state.get("steps", 0)) + 1
    return {"created": created, "steps": steps, "pending": None}


def _build_graph():
    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(ThreadState)
    builder.add_node(_NODE_PICK, _pick)
    builder.add_node(_NODE_ORQUESTADOR, _answer)
    builder.add_node(_NODE_SPECIALIST, _answer)
    builder.add_edge(START, _NODE_PICK)
    builder.add_conditional_edges(
        _NODE_PICK,
        _route,
        {
            _NODE_ORQUESTADOR: _NODE_ORQUESTADOR,
            _NODE_SPECIALIST: _NODE_SPECIALIST,
            "end": END,
        },
    )
    builder.add_edge(_NODE_ORQUESTADOR, _NODE_PICK)
    builder.add_edge(_NODE_SPECIALIST, _NODE_PICK)
    return builder.compile(checkpointer=_CHECKPOINTER)


def _graph():
    """Compiled graph, built once per process. None when langgraph is absent."""
    global _COMPILED
    if not langgraph_available() or _CHECKPOINTER is None:
        return None
    if _COMPILED is None:
        _COMPILED = _build_graph()
    return _COMPILED


def _thread_config(thread_id: int) -> dict[str, str]:
    """Checkpointer key: one LangGraph thread per GallaIA thread."""
    return {"thread_id": f"thread-{thread_id}"}


def run_thread_graph(
    db: Session, thread: Thread, max_steps: int, llm: thread_agents.LLM
) -> tuple[list[Message], list]:
    """Advance `thread` with LangGraph. Returns (created messages, events).

    The caller owns the transaction (commit/refresh/notify), exactly as with
    the classic loop.
    """
    graph = _graph()
    if graph is None:
        raise RuntimeError("langgraph is not installed")

    events: list[ActivityEvent] = []
    state: ThreadState = {
        "thread_id": int(thread.id),
        "max_steps": int(max_steps),
        "steps": 0,
        "handled": [],
        "created": [],
        "pending": None,
    }
    config = {
        "configurable": {
            **_thread_config(thread.id),
            "db": db,
            "thread": thread,
            "llm": llm,
            "events": events,
        },
        # pick + handler per step, plus the no-reply skips and the final pick.
        "recursion_limit": 4 * int(max_steps) + 20,
    }
    final = graph.invoke(dict(state), config) or {}
    created_ids = [int(i) for i in (final.get("created") or [])]
    by_id = {m.id: m for m in thread_agents._load_messages(db, thread.id)}
    created = [by_id[mid] for mid in created_ids if mid in by_id]
    return created, events


def get_thread_graph_state(thread_id: int) -> dict | None:
    """Last checkpointed values of a thread's graph, or None when unknown."""
    graph = _graph()
    if graph is None:
        return None
    try:
        snapshot = graph.get_state({"configurable": _thread_config(thread_id)})
    except Exception:  # noqa: BLE001 — inspection must never break a request
        logger.debug("thread graph state unavailable for thread %s", thread_id)
        return None
    values = dict(getattr(snapshot, "values", None) or {})
    return values or None