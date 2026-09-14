"""Web push VAPID stub — store subscriptions; real send is follow-up.

No ``pywebpush`` dependency. When VAPID env keys are set, ``test`` records a
mock/skipped send. When missing, callers raise ServiceUnavailableError (503).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.exceptions import ServiceUnavailableError
from app.models.push import PushSubscription
from app.schemas.push import PushSubscribeIn, PushSubscriptionOut, PushTestIn, PushTestOut

VAPID_UNCONFIGURED_MSG = (
    "VAPID not configured. Set VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY in the environment "
    "(optional for MVP; do not commit production keys). Real web-push send is a follow-up."
)

REAL_SEND_FOLLOWUP = (
    "Real delivery deferred — install optional pywebpush and wire WebPush when Ociel "
    "provides production VAPID keys. This stub only stores subscriptions and mock-tests."
)


def vapid_configured(settings: Settings) -> bool:
    pub = (settings.vapid_public_key or "").strip()
    priv = (settings.vapid_private_key or "").strip()
    return bool(pub and priv)


def require_vapid(settings: Settings) -> None:
    if not vapid_configured(settings):
        raise ServiceUnavailableError(VAPID_UNCONFIGURED_MSG)


def upsert_subscription(db: Session, payload: PushSubscribeIn) -> PushSubscriptionOut:
    """Store or update a browser PushSubscription (endpoint unique)."""
    endpoint = payload.endpoint.strip()
    existing = db.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )
    now = datetime.now(timezone.utc)
    if existing is None:
        row = PushSubscription(
            endpoint=endpoint,
            p256dh=payload.keys.p256dh,
            auth=payload.keys.auth,
            user_agent=payload.user_agent,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        row = existing
        row.p256dh = payload.keys.p256dh
        row.auth = payload.keys.auth
        if payload.user_agent is not None:
            row.user_agent = payload.user_agent
        row.updated_at = now
    db.commit()
    db.refresh(row)
    return PushSubscriptionOut(
        id=row.id,
        endpoint=row.endpoint,
        created_at=row.created_at,
        updated_at=row.updated_at,
        status="stored",
    )


def mock_test_send(db: Session, payload: PushTestIn | None = None) -> PushTestOut:
    """No-op / skipped send when VAPID is configured (no pywebpush).

    Counts stored subscriptions so the operator can verify the store path.
    Does not call any push service and never uses production secrets.
    """
    body = payload or PushTestIn()
    stmt = select(PushSubscription)
    if body.subscription_id is not None:
        stmt = stmt.where(PushSubscription.id == body.subscription_id)
    rows = list(db.scalars(stmt).all())
    return PushTestOut(
        configured=True,
        sent=False,
        skipped=True,
        reason="pywebpush not configured; mock send only",
        subscription_count=len(rows),
        note=REAL_SEND_FOLLOWUP,
    )
