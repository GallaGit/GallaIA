"""GALLAIA-SEC-011: TrustedHost + Origin guard."""

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.trustedhost import TrustedHostMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app as real_app
from app.middleware.origin_guard import OriginGuardMiddleware

ALLOWED = ["http://localhost:5173", "http://127.0.0.1:5173"]


def _mini_app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/v1/thing")
    def get_thing():
        return {"ok": True}

    @app.post("/api/v1/thing")
    def post_thing():
        return {"ok": True}

    @app.post("/api/v1/triggers/webhook")
    def trigger():
        return {"ok": True}

    app.add_middleware(OriginGuardMiddleware, allowed_origins=ALLOWED)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])
    return app


client = TestClient(_mini_app())


def test_real_app_bad_host_400():
    r = TestClient(real_app).get("/health", headers={"Host": "evil.com"})
    assert r.status_code == 400


def test_real_app_good_host_ok():
    assert TestClient(real_app).get("/health").status_code == 200


def test_real_app_post_evil_origin_403():
    r = TestClient(real_app).post("/api/v1/scheduler/tick", headers={"Origin": "http://evil.com"})
    assert r.status_code == 403


def test_bad_host_400():
    assert client.get("/api/v1/thing", headers={"Host": "attacker.example"}).status_code == 400


def test_proxy_host_with_port_allowed():
    # Vite proxy (changeOrigin) sends Host: 127.0.0.1:8000
    r = client.post("/api/v1/thing", headers={"Host": "127.0.0.1:8000", "Origin": "http://localhost:5173"})
    assert r.status_code == 200


def test_post_evil_origin_403():
    assert client.post("/api/v1/thing", headers={"Origin": "http://evil.com"}).status_code == 403


def test_post_allowed_origin_ok():
    assert client.post("/api/v1/thing", headers={"Origin": "http://localhost:5173"}).status_code == 200


def test_post_same_origin_ok():
    r = client.post("/api/v1/thing", headers={"Host": "127.0.0.1:8000", "Origin": "http://127.0.0.1:8000"})
    assert r.status_code == 200


def test_post_no_origin_ok():
    assert client.post("/api/v1/thing").status_code == 200


def test_get_unaffected_by_origin():
    assert client.get("/api/v1/thing", headers={"Origin": "http://evil.com"}).status_code == 200


def test_triggers_exempt():
    assert client.post("/api/v1/triggers/webhook", headers={"Origin": "http://evil.com"}).status_code == 200
