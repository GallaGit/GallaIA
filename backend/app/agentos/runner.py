"""Session runner: mock kanban advance + tool-event log; optional Anthropic.

Anthropic is used only when ANTHROPIC_API_KEY is set in the environment.
The key is never hardcoded. Without a key, the mock runner always runs.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from app.agentos.models import Session, Task, ToolEvent
from app.agentos.seeds import AgentSeed, get_seed
from app.agentos.store import AgentOSStore, store as default_store

RunnerKind = Literal["mock", "anthropic"]


@dataclass
class RunResult:
    session: Session
    task: Task
    runner: RunnerKind
    used_anthropic: bool
    summary: str
    tool_events: list[ToolEvent] = field(default_factory=list)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _anthropic_key() -> str:
    """Read key from Settings (.env) or process env — never hardcode."""
    try:
        from app.core.config import get_settings

        key = (get_settings().anthropic_api_key or "").strip()
        if key:
            return key
    except Exception:  # noqa: BLE001 — settings may be unavailable in isolation
        pass
    return (os.getenv("ANTHROPIC_API_KEY") or "").strip()


def resolve_runner(preferred: str | None = None) -> RunnerKind:
    """Pick runner. Anthropic only if env key present; else mock."""
    key = _anthropic_key()
    if preferred == "mock":
        return "mock"
    if preferred == "anthropic" and key:
        return "anthropic"
    if preferred in (None, "inherit", "anthropic") and key:
        # Prefer mock for MVP determinism unless explicitly anthropic
        # and key present — ticket: optional Anthropic if key in env.
        if preferred == "anthropic":
            return "anthropic"
    return "mock"


class SessionRunner:
    """Advances a task through the kanban and records tool events."""

    def __init__(self, store: AgentOSStore | None = None) -> None:
        self.store = store or default_store

    def run(
        self,
        task_id: str,
        *,
        agent_name: str | None = None,
        runner: RunnerKind | None = None,
    ) -> RunResult:
        task = self.store.get_task(task_id)
        if task is None:
            raise KeyError(f"Unknown task {task_id!r}")

        seed_name = agent_name or task.assignee_agent
        seed = get_seed(seed_name)
        kind = resolve_runner(runner or seed.runner_preference)

        session = Session(
            task_id=task.id,
            agent_name=seed.name,
            runner=kind,
            status="starting",
        )
        self.store.create_session(session)

        events: list[ToolEvent] = []

        # todo -> doing
        events.append(
            ToolEvent(
                name="kanban.move",
                input={"from": task.status, "to": "doing"},
                output={"ok": True},
            )
        )
        task.status = "doing"
        task.activity.append(f"{seed.name}: started session {session.id} via {kind}")
        session.status = "running"
        self.store.save_task(task)
        self.store.save_session(session)

        # Manifest / tools (least-privilege stub)
        events.append(
            ToolEvent(
                name="session.manifest",
                input={"agent": seed.name},
                output={
                    "mcp": list(seed.mcp),
                    "skills": list(seed.skills),
                    "prompt_origin": seed.prompt_origin,
                },
            )
        )

        used_anthropic = False
        summary: str

        if kind == "anthropic":
            summary, anthropic_events, used_anthropic = self._run_anthropic(seed, task)
            events.extend(anthropic_events)
        else:
            summary, mock_events = self._run_mock(seed, task)
            events.extend(mock_events)

        # doing -> review (agents leave gated work in review; MVP marks review then done)
        events.append(
            ToolEvent(
                name="kanban.move",
                input={"from": "doing", "to": "review"},
                output={"ok": True},
            )
        )
        task.status = "review"
        task.activity.append(f"{seed.name}: work ready for review")

        events.append(
            ToolEvent(
                name="kanban.move",
                input={"from": "review", "to": "done"},
                output={"ok": True, "note": "MVP auto-closes; approval gates come in Phase 3"},
            )
        )
        task.status = "done"
        task.activity.append(f"{seed.name}: finished — {summary}")

        session.tool_events = events
        session.summary = summary
        session.status = "destroyed"
        session.ended_at = _utcnow()

        self.store.save_task(task)
        self.store.save_session(session)

        events.append(
            ToolEvent(
                name="session.destroy",
                input={"session_id": session.id},
                output={"status": "destroyed"},
            )
        )
        session.tool_events = events
        self.store.save_session(session)

        return RunResult(
            session=session,
            task=task,
            runner=kind,
            used_anthropic=used_anthropic,
            summary=summary,
            tool_events=events,
        )

    def _run_mock(self, seed: AgentSeed, task: Task) -> tuple[str, list[ToolEvent]]:
        events = [
            ToolEvent(
                name="agentos.task.read",
                input={"task_id": task.id},
                output={"name": task.name, "description": task.description},
            ),
            ToolEvent(
                name="agentos.task.write_activity",
                input={"message": f"[{seed.name}] mock progress on {task.name}"},
                output={"ok": True},
            ),
        ]
        if seed.name == "plan":
            plan = (
                f"## Implementation plan for: {task.name}\n"
                "1. Clarify acceptance criteria\n"
                "2. Sketch modules and interfaces\n"
                "3. Ordered implementation steps\n"
                "4. Test checklist\n\n"
                f"(Mock plan — {seed.prompt_origin})"
            )
            events.append(
                ToolEvent(
                    name="agentos.task.attach_plan",
                    input={"format": "markdown"},
                    output={"plan_preview": plan[:240]},
                )
            )
            summary = f"Mock plan written for task {task.name!r}"
        elif seed.name == "senior-dev":
            events.append(
                ToolEvent(
                    name="github.commit",
                    input={"message": f"feat: {task.name} (mock)"},
                    output={"sha": "mockdeadbeef", "ok": True},
                )
            )
            summary = f"Mock implementation committed for {task.name!r}"
        else:
            summary = f"Mock default agent completed {task.name!r}"
        return summary, events

    def _run_anthropic(
        self, seed: AgentSeed, task: Task
    ) -> tuple[str, list[ToolEvent], bool]:
        api_key = _anthropic_key()
        events: list[ToolEvent] = []
        if not api_key:
            summary, mock_events = self._run_mock(seed, task)
            events.append(
                ToolEvent(
                    name="anthropic.skip",
                    input={},
                    output={"reason": "ANTHROPIC_API_KEY not set; fell back to mock"},
                )
            )
            events.extend(mock_events)
            return summary, events, False

        model = seed.model
        try:
            from app.core.config import get_settings

            configured = (get_settings().anthropic_model or "").strip()
            if configured:
                model = configured
        except Exception:  # noqa: BLE001
            env_model = (os.getenv("ANTHROPIC_MODEL") or "").strip()
            if env_model:
                model = env_model
        user_msg = (
            f"Task name: {task.name}\n"
            f"Description: {task.description or '(none)'}\n"
            "Respond with a short actionable result for this role only. "
            "Do not invent tools you were not given."
        )
        payload = {
            "model": model,
            "max_tokens": 512,
            "system": f"{seed.foundational_prompt}\n\n{seed.role_prompt}",
            "messages": [{"role": "user", "content": user_msg}],
        }
        events.append(
            ToolEvent(
                name="anthropic.messages.create",
                input={"model": model, "max_tokens": 512},
                output={"status": "calling"},
            )
        )
        try:
            import httpx

            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    content=json.dumps(payload),
                )
            resp.raise_for_status()
            data = resp.json()
            text_parts = [
                block.get("text", "")
                for block in data.get("content", [])
                if block.get("type") == "text"
            ]
            summary = "\n".join(text_parts).strip() or "(empty Anthropic response)"
            events.append(
                ToolEvent(
                    name="anthropic.messages.create",
                    input={"model": model},
                    output={"ok": True, "preview": summary[:400]},
                )
            )
            return summary, events, True
        except Exception as exc:  # noqa: BLE001 — surface as tool event, fall back
            events.append(
                ToolEvent(
                    name="anthropic.error",
                    input={"model": model},
                    output={"error": str(exc)},
                )
            )
            summary, mock_events = self._run_mock(seed, task)
            events.extend(mock_events)
            return f"Anthropic failed ({exc}); mock: {summary}", events, False
