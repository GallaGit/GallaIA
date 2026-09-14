"""Phase 7 slice 4: web push VAPID stub — store + mock test; 503 without keys."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.push import PushSubscription
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty

# Fake test-only VAPID material — NOT production secrets.
TEST_VAPID_PUBLIC = "BP_test_public_key_not_real_aaaaaaaaaaaaaaaaaaaaaaa"
TEST_VAPID_PRIVATE = "test_private_key_not_real_bbbbbbbbbbbbbbbbbbbb"


def _memory_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _sqlite_fk(dbapi_conn, _connection_record):  # noqa: ANN001
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = Session()
    seed_if_empty(db)
    ensure_seed_agents_and_grants(db)
    return db, engine


def _client(db):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def _set_vapid(monkeypatch, *, public: str = TEST_VAPID_PUBLIC, private: str = TEST_VAPID_PRIVATE):
    monkeypatch.setenv("VAPID_PUBLIC_KEY", public)
    monkeypatch.setenv("VAPID_PRIVATE_KEY", private)
    get_settings.cache_clear()


def _clear_vapid(monkeypatch):
    monkeypatch.setenv("VAPID_PUBLIC_KEY", "")
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "")
    monkeypatch.delenv("VAPID_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("VAPID_PRIVATE_KEY", raising=False)
    # Ensure empty strings if Settings reads defaults
    monkeypatch.setenv("VAPID_PUBLIC_KEY", "")
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "")
    get_settings.cache_clear()


def _sub_payload(endpoint: str = "https://push.example/sub/abc123"):
    return {
        "endpoint": endpoint,
        "keys": {
            "p256dh": "client_p256dh_base64url_not_a_secret_xxx",
            "auth": "client_auth_base64url_yyy",
        },
        "user_agent": "pytest",
    }


def test_subscribe_and_test_503_without_vapid(monkeypatch):
    _clear_vapid(monkeypatch)
    db, _engine = _memory_db()
    try:
        client = _client(db)
        res = client.post("/api/v1/push/subscribe", json=_sub_payload())
        assert res.status_code == 503, res.text
        err = res.json()["error"]
        assert err["code"] == "service_unavailable"
        assert "VAPID" in err["message"]

        res2 = client.post("/api/v1/push/test", json={})
        assert res2.status_code == 503, res2.text
        assert "VAPID" in res2.json()["error"]["message"]
    finally:
        db.close()
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_subscribe_stores_and_upserts(monkeypatch):
    _set_vapid(monkeypatch)
    db, _engine = _memory_db()
    try:
        client = _client(db)
        endpoint = "https://push.example/sub/store-me"
        res = client.post("/api/v1/push/subscribe", json=_sub_payload(endpoint))
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "stored"
        assert data["endpoint"] == endpoint
        first_id = data["id"]

        # upsert same endpoint
        payload2 = _sub_payload(endpoint)
        payload2["keys"]["auth"] = "rotated_auth_zzz"
        res2 = client.post("/api/v1/push/subscribe", json=payload2)
        assert res2.status_code == 200, res2.text
        assert res2.json()["id"] == first_id

        rows = list(db.scalars(select(PushSubscription)).all())
        assert len(rows) == 1
        assert rows[0].auth == "rotated_auth_zzz"
        # Never store VAPID private key in SQLite
        dump = str(rows[0].endpoint) + rows[0].p256dh + rows[0].auth
        assert TEST_VAPID_PRIVATE not in dump
    finally:
        db.close()
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_push_test_skips_real_send_when_vapid_set(monkeypatch):
    _set_vapid(monkeypatch)
    db, _engine = _memory_db()
    try:
        client = _client(db)
        client.post("/api/v1/push/subscribe", json=_sub_payload())
        res = client.post(
            "/api/v1/push/test",
            json={"title": "hi", "body": "stub"},
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["configured"] is True
        assert data["sent"] is False
        assert data["skipped"] is True
        assert data["subscription_count"] == 1
        assert "pywebpush" in data["reason"].lower() or "mock" in data["reason"].lower()
    finally:
        db.close()
        app.dependency_overrides.clear()
        get_settings.cache_clear()
