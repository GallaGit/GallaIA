"""Web push VAPID stub endpoints (Phase 7 slice 4)."""

from fastapi import APIRouter

from app.api.dependencies.db import DbSession
from app.core.config import get_settings
from app.schemas.push import PushSubscribeIn, PushSubscriptionOut, PushTestIn, PushTestOut
from app.services.push import mock_test_send, require_vapid, upsert_subscription

router = APIRouter(prefix="/push", tags=["push"])


@router.post("/subscribe", response_model=PushSubscriptionOut)
def api_push_subscribe(payload: PushSubscribeIn, db: DbSession):
    """Store a browser PushSubscription.

    Requires VAPID_PUBLIC_KEY + VAPID_PRIVATE_KEY in env (503 if missing).
    Does not send a push; client-generated keys only are persisted.
    """
    require_vapid(get_settings())
    return upsert_subscription(db, payload)


@router.post("/test", response_model=PushTestOut)
def api_push_test(db: DbSession, payload: PushTestIn | None = None):
    """Mock / skipped test send when VAPID is configured; 503 if not.

    Real HTTP push via pywebpush is intentionally not wired in this stub.
    """
    require_vapid(get_settings())
    return mock_test_send(db, payload)
