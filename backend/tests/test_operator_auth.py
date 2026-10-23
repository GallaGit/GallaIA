"""Operator bearer-token gate for every /api/v1 route (webhook stays signed)."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.seed import ensure_seed_agents_and_grants, seed_if_empty

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_OPERATOR_TOKEN = "test-operator-token-0123456789abcdefghijklmnopqrstuv"
TEST_WEBHOOK_SECRET = "test-operator-auth-webhook-secret"
WRONG_TOKEN = "Bearer wrong-token-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
WEBHOOK_PATH = "/api/v1/triggers/webhook"


def _collect_routes(routes) -> list[tuple[set[str], str]]:  # noqa: ANN001
    collected: list[tuple[set[str], str]] = []
    for route in routes:
        if isinstance(route, APIRoute):
            collected.append((route.methods, route.path))
            continue
        effective = getattr(route, "effective_route_contexts", None)
        if callable(effective):
            for context in effective():
                original = getattr(context, "original_route", None)
                path = getattr(context, "path", None)
                if isinstance(original, APIRoute) and path:
                    collected.append((original.methods, path))
            continue
        original_router = getattr(route, "original_router", None)
        if original_router is not None:
            collected.extend(_collect_routes(original_router.routes))
    return collected


def _api_routes() -> list[tuple[str, str]]:
    routes: list[tuple[str, str]] = []
    for methods, route_path in _collect_routes(app.routes):
        if not route_path.startswith("/api/v1"):
            continue
        if route_path == WEBHOOK_PATH:
            continue
        path = re.sub(r"\{[^}]+\}", "1", route_path)
        for method in sorted(methods):
            if method in {"HEAD", "OPTIONS"}:
                continue
            routes.append((method, path))
    return routes


API_ROUTES = _api_routes()


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


def _client_without_auth() -> TestClient:
    client = TestClient(app, raise_server_exceptions=False)
    client.headers.pop("Authorization")
    return client


def _request_status(
    client: TestClient,
    method: str,
    path: str,
    headers: dict[str, str] | None = None,
) -> int:
    if "stream" in path:
        with client.stream(method, path, headers=headers) as response:
            return response.status_code
    kwargs: dict[str, object] = {}
    if headers:
        kwargs["headers"] = headers
    if method in {"POST", "PUT", "PATCH"}:
        kwargs["json"] = {}
    return client.request(method, path, **kwargs).status_code


@pytest.mark.parametrize(
    ("method", "path"),
    API_ROUTES,
    ids=[f"{method} {path}" for method, path in API_ROUTES],
)
def test_api_routes_require_operator_token(method: str, path: str):
    response = _client_without_auth().request(
        method,
        path,
        **({"json": {}} if method in {"POST", "PUT", "PATCH"} else {}),
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


@pytest.mark.parametrize(
    ("method", "path"),
    API_ROUTES,
    ids=[f"{method} {path}" for method, path in API_ROUTES],
)
def test_api_routes_reject_wrong_operator_token(method: str, path: str):
    client = TestClient(
        app,
        raise_server_exceptions=False,
        headers={"Authorization": WRONG_TOKEN},
    )
    assert _request_status(client, method, path) == 401


@pytest.mark.parametrize(
    ("method", "path"),
    API_ROUTES,
    ids=[f"{method} {path}" for method, path in API_ROUTES],
)
def test_api_routes_accept_correct_operator_token(
    method: str,
    path: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("GALLAIA_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)
    get_settings.cache_clear()
    try:
        client = TestClient(app, raise_server_exceptions=False)
        status = _request_status(
            client,
            method,
            path,
            headers={"X-Webhook-Secret": TEST_WEBHOOK_SECRET},
        )
        assert status != 401
    finally:
        get_settings.cache_clear()


def test_health_is_open_without_authorization():
    response = _client_without_auth().get("/health")
    assert response.status_code == 200


def test_webhook_keeps_webhook_secret_auth(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GALLAIA_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)
    get_settings.cache_clear()
    db, engine = _memory_db()

    def _override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    try:
        client = _client_without_auth()
        assert "Authorization" not in client.headers

        ok = client.post(
            WEBHOOK_PATH,
            headers={"X-Webhook-Secret": TEST_WEBHOOK_SECRET},
            json={"shape": "generic", "name": "operator-auth-webhook"},
        )
        assert ok.status_code == 201, ok.text

        bad = client.post(
            WEBHOOK_PATH,
            headers={"X-Webhook-Secret": "wrong"},
            json={"shape": "generic"},
        )
        assert bad.status_code == 401
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()
        get_settings.cache_clear()


def test_disallowed_host_is_rejected():
    client = _client_without_auth()
    response = client.get("/health", headers={"Host": "evil.example"})
    assert response.status_code == 400


def test_settings_requires_operator_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GALLAIA_OPERATOR_TOKEN", raising=False)
    with pytest.raises(ValidationError) as missing:
        Settings(_env_file=None)
    assert "GALLAIA_OPERATOR_TOKEN" in str(missing.value)


def test_settings_rejects_short_operator_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GALLAIA_OPERATOR_TOKEN", "short-tok")
    with pytest.raises(ValidationError) as short:
        Settings(_env_file=None)
    assert "GALLAIA_OPERATOR_TOKEN" in str(short.value)


def test_app_import_fails_without_operator_token(tmp_path: Path):
    env = os.environ.copy()
    env.pop("GALLAIA_OPERATOR_TOKEN", None)
    env.pop("gallaia_operator_token", None)
    env["PYTHONPATH"] = str(BACKEND_DIR)

    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "GALLAIA_OPERATOR_TOKEN" in result.stderr
    assert TEST_OPERATOR_TOKEN not in result.stderr
