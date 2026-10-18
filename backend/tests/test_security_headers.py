"""GALLAIA-SEC-007: CSP + basic security headers on SPA, API, SSE and docs."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, StreamingResponse
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.main as main
from app.middleware.security_headers import (
    API_CSP,
    DOCS_CSP,
    SecurityHeadersMiddleware,
    csp_for_path,
)
from tests.test_thread_stream import (  # reuse in-memory DB helpers
    _client,
    _memory_db,
    _new_thread_with_user_text,
    _teardown,
)

COMMON = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
}


def _assert_common(headers):
    for name, value in COMMON.items():
        assert headers.get(name) == value, name
    assert "frame-ancestors 'none'" in headers["content-security-policy"]


@pytest.fixture()
def spa_client(tmp_path, monkeypatch):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html>SPA_INDEX</html>")
    (static / "favicon.svg").write_text("<svg/>")
    (static / "sw.js").write_text("self.addEventListener('fetch', () => {})")
    (static / "manifest.webmanifest").write_text("{}")
    monkeypatch.setattr(main, "STATIC_DIR", static.resolve())
    with TestClient(main.app) as c:
        yield c


def test_spa_index_has_strict_csp(spa_client):
    r = spa_client.get("/")
    assert r.status_code == 200
    assert "SPA_INDEX" in r.text
    _assert_common(r.headers)
    csp = r.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self';" in csp
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp
    assert "object-src 'none'" in csp
    # Google Fonts loaded from index.html must keep working.
    assert "https://fonts.googleapis.com" in csp
    assert "https://fonts.gstatic.com" in csp
    # API + SSE (EventSource) from the same origin.
    assert "connect-src 'self'" in csp
    assert "worker-src 'self'" in csp
    assert "manifest-src 'self'" in csp


def test_spa_client_route_and_static_files(spa_client):
    r = spa_client.get("/threads/123")
    assert r.status_code == 200 and "SPA_INDEX" in r.text
    _assert_common(r.headers)
    assert "default-src 'self'" in r.headers["content-security-policy"]

    js = spa_client.get("/sw.js")
    assert js.status_code == 200
    assert js.headers["content-type"].startswith("text/javascript")
    _assert_common(js.headers)

    svg = spa_client.get("/favicon.svg")
    assert svg.headers["content-type"].startswith("image/svg+xml")

    manifest = spa_client.get("/manifest.webmanifest")
    assert manifest.headers["content-type"].startswith("application/manifest+json")


def test_api_and_health_have_locked_down_csp():
    client = TestClient(main.app)
    for path in ("/health", "/api/v1/projects"):
        r = client.get(path)
        assert r.status_code == 200, path
        _assert_common(r.headers)
        assert r.headers["content-security-policy"] == API_CSP


def test_guard_rejections_also_carry_headers():
    client = TestClient(main.app)
    r = client.get("/health", headers={"Host": "evil.com"})
    assert r.status_code == 400
    _assert_common(r.headers)
    r = client.post("/api/v1/scheduler/tick", headers={"Origin": "http://evil.com"})
    assert r.status_code == 403
    _assert_common(r.headers)


def test_docs_get_relaxed_csp_only_on_docs():
    client = TestClient(main.app)
    r = client.get("/docs")
    if r.status_code == 404:  # APP_ENV=production disables docs
        pytest.skip("docs disabled")
    assert r.headers["content-security-policy"] == DOCS_CSP
    _assert_common(r.headers)
    assert "unsafe-inline" not in csp_for_path("/")
    assert csp_for_path("/docsx").startswith("default-src 'self'; script-src 'self';")


def test_thread_sse_stream_still_works_with_headers():
    db, _engine, Session = _memory_db()
    try:
        client = _client(db, Session)
        thread_id = _new_thread_with_user_text(client)
        r = client.get(f"/api/v1/threads/{thread_id}/stream")
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
        assert "event:" in r.text
        _assert_common(r.headers)
        assert r.headers["content-security-policy"] == API_CSP
    finally:
        _teardown(db)


def _mini_app(**kwargs) -> FastAPI:
    app = FastAPI()

    @app.get("/stream")
    def stream():
        def gen():
            for i in range(3):
                yield f"data: {i}\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.get("/custom")
    def custom():
        return PlainTextResponse(
            "ok", headers={"Content-Security-Policy": "default-src 'none'", "Referrer-Policy": "same-origin"}
        )

    app.add_middleware(SecurityHeadersMiddleware, **kwargs)
    return app


def test_streaming_body_is_not_altered():
    r = TestClient(_mini_app()).get("/stream")
    assert r.text == "data: 0\n\ndata: 1\n\ndata: 2\n\n"
    assert r.headers["x-content-type-options"] == "nosniff"


def test_route_headers_are_not_overridden():
    r = TestClient(_mini_app()).get("/custom")
    assert r.headers["content-security-policy"] == "default-src 'none'"
    assert r.headers["referrer-policy"] == "same-origin"
    assert r.headers["x-frame-options"] == "DENY"


def test_extra_connect_src():
    r = TestClient(_mini_app(extra_connect_src=["http://127.0.0.1:9000"])).get("/stream")
    # /stream is a SPA-policy path in the mini app
    assert "connect-src 'self' http://127.0.0.1:9000;" in r.headers["content-security-policy"]
