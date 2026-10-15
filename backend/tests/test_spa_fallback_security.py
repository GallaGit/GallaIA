"""GALLAIA-SEC-001: spa_fallback must never serve files outside STATIC_DIR."""

import pytest
from fastapi.testclient import TestClient

import app.main as main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html>SPA_INDEX</html>")
    (static / "favicon.svg").write_text("<svg/>")
    (tmp_path / "secret.txt").write_text("TOP_SECRET")
    monkeypatch.setattr(main, "STATIC_DIR", static.resolve())
    with TestClient(main.app) as c:
        yield c


@pytest.mark.parametrize(
    "path",
    [
        "/..%2Fsecret.txt",
        "/..%2F..%2F..%2F..%2Fetc%2Fhostname",
        "/%2e%2e/secret.txt",
        "/%2e%2e%2f%2e%2e%2fsecret.txt",
        "/%2Fetc%2Fpasswd",
        "/%2F%2Fetc%2Fpasswd",
        "/%2Fproc%2Fself%2Fenviron",
        "/..%2F..%2F..%2F..%2F..%2Fproc%2Fself%2Fenviron",
    ],
)
def test_traversal_returns_404(client, path):
    r = client.get(path)
    assert r.status_code == 404
    assert "TOP_SECRET" not in r.text
    assert "SPA_INDEX" not in r.text


def test_spa_route_serves_index(client):
    r = client.get("/agents/some-id")
    assert r.status_code == 200
    assert "SPA_INDEX" in r.text


def test_static_file_inside_dir_served(client):
    r = client.get("/favicon.svg")
    assert r.status_code == 200
    assert r.text == "<svg/>"
