"""Runtime engines (F2.2): optional LangGraph thread engine.

`app.runtime.thread_graph` mirrors the classic loop in
`app.services.thread_agents.advance_thread`. LangGraph is an optional
dependency (like litellm): when it is not installed the classic loop runs.
"""

from app.runtime.thread_graph import (
    LANGGRAPH,
    CLASSIC,
    ThreadState,
    get_thread_graph_state,
    langgraph_available,
    pending_approval,
    resume_thread_approval,
    run_thread_graph,
    thread_approval_enabled,
    thread_engine,
)

__all__ = [
    "CLASSIC",
    "LANGGRAPH",
    "ThreadState",
    "get_thread_graph_state",
    "langgraph_available",
    "pending_approval",
    "resume_thread_approval",
    "run_thread_graph",
    "thread_approval_enabled",
    "thread_engine",
]