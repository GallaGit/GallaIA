"""Phase 5 Triggers — signed webhook request/response."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

WebhookShape = Literal["generic", "support-inbound", "bug-report"]


class WebhookTriggerIn(BaseModel):
    """Optional body for POST /triggers/webhook."""

    shape: WebhookShape = "generic"
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    payload: dict[str, Any] | None = None


class WebhookTriggerOut(BaseModel):
    task_id: int
    session_id: int
    shape: WebhookShape
    runner: str = "webhook"
    agent_name: str | None = None


class LeadStatusNuevoIn(BaseModel):
    """Body for POST /triggers/lead-status-nuevo."""

    leadId: str | int | None = Field(default=None, description="CRM lead id")


class LeadStatusNuevoOut(BaseModel):
    lead_id: str
    template_id: int
    template_slug: str
    run_id: str
    task_ids: list[int]
    task_count: int
