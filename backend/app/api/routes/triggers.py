"""Phase 5 Triggers — public signed webhook."""

from fastapi import APIRouter, Header

from app.api.dependencies.db import DbSession
from app.api.dependencies.settings import SettingsDep
from app.schemas.trigger import WebhookTriggerIn, WebhookTriggerOut
from app.services.triggers import handle_webhook_trigger

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
