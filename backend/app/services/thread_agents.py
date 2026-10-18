"""F1.2 — Agents reply to each other inside a thread (backend only).

`advance_thread` walks the pending agent-addressed messages oldest first and
lets the addressed agent answer: orquestador plans and delegates, FE/BE return
results, then orquestador summarises to the human. One step == one answered
message, capped by `max_steps` so a reply can never start a loop.
"""

from __future__ import annotations

import json
import re
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agentos.seeds import get_seed
from app.exceptions import ConflictError
from app.models import Message, Thread
from app.models.thread import HUMAN_ACTOR
from app.services.activity import append_activity, notify_after_commit

AGENT_NAMES = ("orquestador", "fe", "be")
AGENT_SET = frozenset(AGENT_NAMES)
DELEGATABLE = ("fe", "be")

LLM = Callable[[str, str], str]

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)
_FENCE = re.compile(r"^```[a-zA-Z0-9_-]*\n?|\n?```$")


def _agent_system(name: str) -> str:
    """Foundational + role prompt for a seeded agent (falls back to the slug)."""
    try:
        seed = get_seed(name)
    except KeyError:
        return f"You are {name} in GallaIA."
    return f"{seed.foundational_prompt}\n\n{seed.role_prompt}"


def mock_llm(system: str, user: str) -> str:
    """Deterministic offline stand-in. Never touches the network."""
    low = system.lower()
    if "\u2014 fe" in low:
        return f"[fe] mock result: {user}"
    if "\u2014 be" in low:
        return f"[be] mock result: {user}"
    if "\u2014 orquestador" in low:
        # Non-JSON on purpose: the planner falls back to delegating to FE and BE.
        return f"[orquestador] mock plan for: {user}"
    return f"[agent] mock: {user}"


def _agent_model(
    db: Session | None, name: str, project_id: int | None = None
) -> str | None:
    """Agent.model from the DB (UI/CLI editable), else the seed default."""
    if db is not None:
        from app.models import Agent

        query = select(Agent.model).where(Agent.name == name)
        if project_id is not None:
            query = query.order_by((Agent.project_id != project_id), Agent.id)
        else:
            query = query.order_by(Agent.id)
        model = db.scalar(query.limit(1))
        if model:
            return model
    try:
        return get_seed(name).model
    except KeyError:
        return None


class GatewayLLM:
    """LLM callable backed by the F2.1 gateway, with per-agent model + usage log."""

    def __init__(
        self,
        db: Session | None = None,
        thread_id: int | None = None,
        project_id: int | None = None,
    ) -> None:
        self.db = db
        self.thread_id = thread_id
        self.project_id = project_id
        self.calls = 0

    def __call__(self, system: str, user: str, agent: str | None = None) -> str:
        from app.llm import gateway

        sink = None
        if self.db is not None:
            from app.llm.usage import db_usage_sink

            sink = db_usage_sink(
                self.db, source="thread", agent=agent, thread_id=self.thread_id
            )
        model = _agent_model(self.db, agent, self.project_id) if agent else None
        self.calls += 1
        return gateway.complete(system, user, model=model, on_usage=sink).text


def default_llm(
    db: Session | None = None,
    thread_id: int | None = None,
    project_id: int | None = None,
) -> LLM:
    """OpenRouter -> Groq -> mock, through the F2.1 gateway."""
    from app.llm import gateway

    if not gateway.configured_providers():
        return mock_llm
    return GatewayLLM(db, thread_id, project_id)


def _ask(llm: LLM, agent: str, system: str, user: str) -> str:
    """Call the LLM; the gateway one also gets the agent (model + usage)."""
    if isinstance(llm, GatewayLLM):
        return llm(system, user, agent=agent)
    return llm(system, user)


def _load_messages(db: Session, thread_id: int) -> list[Message]:
    return list(
        db.scalars(
            select(Message).where(Message.thread_id == thread_id).order_by(Message.id)
        ).all()
    )


def _is_answered(messages: list[Message], msg: Message) -> bool:
    """Answered when the addressed agent sent any later message in the thread."""
    return any(m.id > msg.id and m.sender == msg.recipient for m in messages)


def _next_pending(messages: list[Message], handled: set[int]) -> Message | None:
    for msg in messages:
        if msg.recipient not in AGENT_SET:
            continue
        if msg.sender == msg.recipient:  # never answer yourself
            continue
        if msg.id in handled:
            continue
        if _is_answered(messages, msg):
            continue
        return msg
    return None


def _extract_json(raw: str) -> dict | None:
    text = (raw or "").strip()
    text = _FENCE.sub("", text).strip()
    candidates = [text]
    match = _JSON_BLOCK.search(text)
    if match:
        candidates.append(match.group(0))
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except (TypeError, ValueError):
            continue
        if isinstance(data, dict):
            return data
    return None


def _parse_plan(raw: str, user_text: str) -> tuple[str, list[tuple[str, str]]]:
    """Defensively read {"plan", "delegations"}; fall back to FE + BE."""
    data = _extract_json(raw)
    plan = ""
    delegations: list[tuple[str, str]] = []
    if data is not None:
        if isinstance(data.get("plan"), str):
            plan = data["plan"].strip()
        items = data.get("delegations")
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                to = item.get("to")
                brief = item.get("brief")
                if to not in DELEGATABLE or not isinstance(brief, str):
                    continue
                if not brief.strip() or any(t == to for t, _ in delegations):
                    continue
                delegations.append((to, brief.strip()))
                if len(delegations) >= 2:
                    break
    if not delegations:
        delegations = [("fe", user_text), ("be", user_text)]
    return plan, delegations


def _message(thread_id: int, sender: str, recipient: str | None, kind: str, body: str) -> Message:
    return Message(
        thread_id=thread_id,
        sender=sender,
        recipient=recipient,
        kind=kind,
        body=body,
    )


def _orquestador_plan(thread: Thread, msg: Message, llm: LLM) -> list[Message]:
    raw = _ask(llm, "orquestador", _agent_system("orquestador"), msg.body)
    plan, delegations = _parse_plan(raw, msg.body)
    if not plan:
        plan = f"Plan: atender \u00ab{msg.body}\u00bb coordinando FE y BE."
    out = [_message(thread.id, "orquestador", None, "text", plan)]
    for to, brief in delegations:
        out.append(_message(thread.id, "orquestador", to, "delegation", brief))
    return out


def _orquestador_summary(thread: Thread, messages: list[Message]) -> list[Message]:
    delegations = [
        m for m in messages if m.sender == "orquestador" and m.kind == "delegation"
    ]
    if not delegations:
        return []
    results = [m for m in messages if m.kind == "result" and m.sender in DELEGATABLE]
    answers: list[Message] = []
    for delegation in delegations:
        matched = next(
            (
                r
                for r in results
                if r.sender == delegation.recipient and r.id > delegation.id
            ),
            None,
        )
        if matched is None:
            return []  # wait for the remaining results
        answers.append(matched)
    summary = "Resumen del orquestador: " + " | ".join(
        f"{r.sender}: {r.body}" for r in answers
    )
    return [_message(thread.id, "orquestador", HUMAN_ACTOR, "text", summary)]


def _handle_orquestador(
    thread: Thread, msg: Message, messages: list[Message], llm: LLM
) -> list[Message]:
    if msg.kind == "text" and msg.sender == HUMAN_ACTOR:
        return _orquestador_plan(thread, msg, llm)
    if msg.kind == "result":
        return _orquestador_summary(thread, messages)
    return []


def _handle_specialist(thread: Thread, msg: Message, llm: LLM) -> list[Message]:
    if msg.kind != "delegation":
        return []
    agent = msg.recipient
    assert agent in DELEGATABLE
    text = (_ask(llm, agent, _agent_system(agent), msg.body) or "").strip()
    if not text:
        text = f"[{agent}] mock result: {msg.body}"
    return [_message(thread.id, agent, "orquestador", "result", text)]


def advance_thread(
    db: Session,
    thread: Thread,
    max_steps: int = 6,
    llm: LLM | None = None,
) -> list[Message]:
    """Let addressed agents answer pending messages. Returns created messages."""
    if thread.status == "closed":
        raise ConflictError(f"Thread {thread.id} is closed")

    run_llm = llm or default_llm(db, thread.id, thread.project_id)
    max_steps = max(1, int(max_steps))
    created: list[Message] = []
    events = []
    handled: set[int] = set()
    steps = 0

    while steps < max_steps:
        messages = _load_messages(db, thread.id)
        pending = _next_pending(messages, handled)
        if pending is None:
            break

        if pending.recipient == "orquestador":
            replies = _handle_orquestador(thread, pending, messages, run_llm)
        else:
            replies = _handle_specialist(thread, pending, run_llm)

        if not replies:  # undefined pair → handled implicitly, no reply
            handled.add(pending.id)
            continue

        for reply in replies:
            db.add(reply)
            db.flush()
            events.append(
                append_activity(
                    db,
                    type="message.created",
                    message=f"Message in thread {thread.id} from {reply.sender}",
                )
            )
            created.append(reply)
        steps += 1

    if created or (isinstance(run_llm, GatewayLLM) and run_llm.calls):
        db.commit()  # replies + llm_usage rows
        for reply in created:
            db.refresh(reply)
        for event in events:
            notify_after_commit(event)
    return created
