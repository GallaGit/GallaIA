"""Phase 5 Triggers — public signed webhook + lead-status-nuevo."""

from fastapi import APIRouter, Header

from app.api.dependencies.db import DbSession
from app.api.dependencies.settings import SettingsDep
from app.schemas.trigger import (
    LeadStatusNuevoIn,
    LeadStatusNuevoOut,
    WebhookTriggerIn,
    WebhookTriggerOut,
)
from app.services.triggers import handle_lead_status_nuevo, handle_webhook_trigger

router = APIRouter(prefix="/triggers", tags=["triggers"])


@router.post("/webhook", response_model=WebhookTriggerOut, status_code=201)
def post_webhook_trigger(
    db: DbSession,
    settings: SettingsDep,
    payload: WebhookTriggerIn | None = None,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
):
    """Public webhook. Valid `X-Webhook-Secret` -> task + session stub; else 401."""
    return handle_webhook_trigger(
        db,
        settings=settings,
        secret_header=x_webhook_secret,
        body=payload,
    )


@router.post("/lead-status-nuevo", response_model=LeadStatusNuevoOut, status_code=200)
def post_lead_status_nuevo(
    db: DbSession,
    settings: SettingsDep,
    payload: LeadStatusNuevoIn | None = None,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
):
    """CRM lead.status=nuevo -> instantiate lead-intake-workflow (2 cards)."""
    return handle_lead_status_nuevo(
        db,
        settings=settings,
        secret_header=x_webhook_secret,
        body=payload,
    )
