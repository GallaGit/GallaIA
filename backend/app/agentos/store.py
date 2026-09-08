"""Process-local store for AgentOS MVP tasks and sessions."""

from __future__ import annotations

from threading import Lock

from app.agentos.models import Session, Task


class AgentOSStore:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()

    def create_task(self, task: Task) -> Task:
        with self._lock:
            self._tasks[task.id] = task
            return task

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[Task]:
        return list(self._tasks.values())

    def save_task(self, task: Task) -> Task:
        with self._lock:
            task.touch()
            self._tasks[task.id] = task
            return task

    def create_session(self, session: Session) -> Session:
        with self._lock:
            self._sessions[session.id] = session
            return session

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def save_session(self, session: Session) -> Session:
        with self._lock:
            self._sessions[session.id] = session
            return session

    def list_sessions(self) -> list[Session]:
        return list(self._sessions.values())


store = AgentOSStore()
