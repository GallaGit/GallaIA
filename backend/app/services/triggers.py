"""Phase 5 Triggers — signed public webhook -> task + session stub.

Auth: shared secret via header `X-Webhook-Secret` compared to
`Settings.gallaia_webhook_secret` (env `GALLAIA_WEBHOOK_SECRET`).
Bad/missing/misconfigured secret -> 401. Valid -> scoped task + queued session.
"""

from __future__ import annotations

import json
import secrets
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.exceptions import BadRequestError, UnauthorizedError
from app.models import Agent, AgentSession, Project, Task
from app.schemas.trigger import (
    LeadStatusNuevoIn,
    LeadStatusNuevoOut,
    WebhookShape,
    WebhookTriggerIn,
    WebhookTriggerOut,
)
from app.services.activity import append_activity, notify_after_commit
from app.services.templates import (
    LEAD_INTAKE_SLUG,
    get_template,
    instantiate_template,
)

# Seed agent preferred per inbound shape (lean Phase 5 slice 1).
SHAPE_AGENT: dict[str, str] = {
    "generic": "default",
    "support-inbound": "support",
    "bug-report": "senior-dev",
}

RUNNER = "webhook"


def verify_webhook_secret(provided: str | None, settings: Settings) -> None:
    """Constant-time compare against configured secret. Empty config denies."""
    expected = (settings.gallaia_webhook_secret or "").strip()
    if not expected:
        raise UnauthorizedError("Webhook secret not configured")
    got = (provided or "").strip()
    if not got or not secrets.compare_digest(got, expected):
        raise UnauthorizedError("Invalid webhook secret")


def _default_project(db: Session) -> Project:
    project = db.scalar(select(Project).where(Project.slug == "default"))
    if project is None:
        raise BadRequestError("Default project missing; seed the database first")
    return project


def _agent_for_shape(db: Session, shape: WebhookShape) -> Agent:
    name = SHAPE_AGENT.get(shape, "default")
    agent = db.scalar(select(Agent).where(Agent.name == name))
    if agent is None:
        # Fall back to any agent so tests/dev still get a stub.
        agent = db.scalar(select(Agent).order_by(Agent.id.asc()))
    if agent is None:
        raise BadRequestError("No agent available for webhook stub")
    return agent


def _task_name(payload: WebhookTriggerIn) -> str:
    if payload.name and payload.name.strip():
        return payload.name.strip()[:200]
    return {
        "support-inbound": "support-inbound",
        "bug-report": "bug-report",
        "generic": "webhook-inbound",
    }.get(payload.shape, "webhook-inbound")


def _task_description(payload: WebhookTriggerIn) -> str | None:
    parts: list[str] = []
    if payload.description and payload.description.strip():
        parts.append(payload.description.strip())
    if payload.payload is not None:
        parts.append("payload: " + json.dumps(payload.payload, ensure_ascii=False))
    if not parts:
        return f"Created by signed webhook (shape={payload.shape})"
    return "\n".join(parts)


def handle_webhook_trigger(
    db: Session,
    *,
    settings: Settings,
    secret_header: str | None,
    body: WebhookTriggerIn | None = None,
) -> WebhookTriggerOut:
    """Validate secret then create task + queued session stub."""
    verify_webhook_secret(secret_header, settings)

    payload = body or WebhookTriggerIn()
    project = _default_project(db)
    agent = _agent_for_shape(db, payload.shape)

    task = Task(
        project_id=project.id,
        name=_task_name(payload),
        description=_task_description(payload),
        status="todo",
        assignee_agent_id=agent.id,
    )
    db.add(task)
    db.flush()

    stub = AgentSession(
        agent_id=agent.id,
        task_id=task.id,
        runner=RUNNER,
        status="queued",
        summary=f"webhook trigger shape={payload.shape}",
        tool_call_log="[]",
    )
    db.add(stub)
    db.flush()
    evt = append_activity(
        db,
        type="webhook.received",
        message=f"Webhook received shape={payload.shape} task={task.name}",
        task_id=task.id,
        session_id=stub.id,
    )
    db.commit()
    db.refresh(task)
    db.refresh(stub)
    notify_after_commit(evt)

    return WebhookTriggerOut(
        task_id=task.id,
        session_id=stub.id,
        shape=payload.shape,
        runner=RUNNER,
        agent_name=agent.name,
    )


def handle_lead_status_nuevo(
    db: Session,
    *,
    settings: Settings,
    secret_header: str | None,
    body: LeadStatusNuevoIn | None = None,
) -> LeadStatusNuevoOut:
    """Validate secret + leadId, then instantiate lead-intake-workflow (2 cards)."""
    verify_webhook_secret(secret_header, settings)

    payload = body or LeadStatusNuevoIn()
    raw = payload.leadId
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise BadRequestError("leadId is required")

    lead_id = str(raw).strip()
    template = get_template(db, LEAD_INTAKE_SLUG)
    result = instantiate_template(
        db,
        template,
        name_prefix=f"Lead #{lead_id} — ",
    )
    task_ids = [t.id for t in result.tasks]
    return LeadStatusNuevoOut(
        lead_id=lead_id,
        template_id=result.template_id,
        template_slug=result.template_slug,
        run_id=result.run_id,
        task_ids=task_ids,
        task_count=len(task_ids),
    )

