"""Web push VAPID stub schemas (Phase 7 slice 4)."""

from datetime import datetime

from pydantic import BaseModel, Field


class PushSubscriptionKeys(BaseModel):
    p256dh: str = Field(min_length=1, description="Browser-generated ECDH public key (base64url).")
    auth: str = Field(min_length=1, description="Browser-generated auth secret (base64url).")


class PushSubscribeIn(BaseModel):
    """Standard PushSubscription JSON shape from the browser."""

    endpoint: str = Field(min_length=8, description="Push service endpoint URL.")
    keys: PushSubscriptionKeys
    user_agent: str | None = Field(default=None, max_length=512)


class PushSubscriptionOut(BaseModel):
    id: int
    endpoint: str
    created_at: datetime
    updated_at: datetime
    status: str = "stored"

    model_config = {"from_attributes": True}


class PushTestIn(BaseModel):
    """Optional body for test send; defaults to all stored subscriptions."""

    subscription_id: int | None = Field(
        default=None,
        description="If set, target one stored subscription; else use all.",
    )
    title: str = Field(default="GallaIA test", max_length=120)
    body: str = Field(default="Web push stub (no real delivery).", max_length=500)


class PushTestOut(BaseModel):
    configured: bool
    sent: bool
    skipped: bool
    reason: str
    subscription_count: int = 0
    note: str = ""
