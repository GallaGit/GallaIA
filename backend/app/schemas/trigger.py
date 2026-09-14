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
