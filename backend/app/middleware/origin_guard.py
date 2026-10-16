"""GALLAIA-SEC-011: reject cross-site state-changing requests to /api/v1.

If an ``Origin`` header is present on POST/PUT/PATCH/DELETE under /api/v1 it must
be either a configured CORS origin or the same origin as the request (Host).
A missing Origin (curl, server-to-server) is allowed. ``/api/v1/triggers`` is
exempt because it is protected by the webhook secret.
"""

from urllib.parse import urlsplit

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
API_PREFIX = "/api/v1"
EXEMPT_PREFIXES = ("/api/v1/triggers",)


class OriginGuardMiddleware:
    def __init__(self, app: ASGIApp, allowed_origins: list[str]) -> None:
        self.app = app
        self.allowed = {o.rstrip("/").lower() for o in allowed_origins}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] in UNSAFE_METHODS:
            path = scope["path"]
            if (path == API_PREFIX or path.startswith(API_PREFIX + "/")) and not path.startswith(
                EXEMPT_PREFIXES
            ):
                headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
                origin = headers.get("origin")
                if origin is not None and not self._origin_ok(origin, headers.get("host", "")):
                    response = JSONResponse({"detail": "Origin not allowed"}, status_code=403)
                    await response(scope, receive, send)
                    return
        await self.app(scope, receive, send)

    def _origin_ok(self, origin: str, host: str) -> bool:
        origin = origin.strip().rstrip("/").lower()
        if origin in self.allowed:
            return True
        # Same-origin (e.g. UI served by the backend at http://127.0.0.1:8000).
        parts = urlsplit(origin)
        return bool(parts.netloc) and parts.scheme in {"http", "https"} and parts.netloc == host.lower()
