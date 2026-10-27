"""Phase 5 Triggers — signed webhook request/response."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

WebhookShape = Literal["generic", "support-inbound", "bug-report"]


class WebhookTriggerIn(BaseModel):
    """Optional body for POST /triggers/webhook."""

    shape: WebhookShape = "generic"
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    payload: dict[str, Any] | None = None

    @field_validator("payload")
    @classmethod
    def _validate_payload_size(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        import json

        if len(json.dumps(value)) > 20000:
            raise ValueError("payload too large")
        return value


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
