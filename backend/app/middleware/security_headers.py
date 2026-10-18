"""GALLAIA-SEC-007: Content-Security-Policy and basic security headers.

Pure ASGI middleware (no response buffering), so it is safe for the SSE
endpoints (``text/event-stream``): headers are added to ``http.response.start``
and the body is streamed untouched.

Three policies:

* SPA (``/``, client routes, ``/assets``…): strict ``default-src 'self'``. The
  only third-party origins are Google Fonts, loaded from ``index.html``.
* API / health (``/api``, ``/health``): ``default-src 'none'`` — JSON and SSE
  never need to load anything.
* Swagger UI / ReDoc (``/docs``, ``/redoc``; disabled in production): FastAPI
  renders them with an inline script and assets from jsDelivr, so they get a
  relaxed policy scoped to those two paths only.

In dev (``npm run dev``) the page is served by Vite, so these headers only reach
the proxied ``/api`` responses, where they are harmless for ``fetch`` and
``EventSource``.
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

SPA_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self'{extra_connect}; "
    "manifest-src 'self'; "
    "worker-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)

API_CSP = "default-src 'none'; frame-ancestors 'none'"

DOCS_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.redoc.ly; "
    "worker-src 'self' blob:; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "frame-ancestors 'none'"
)

DOCS_PATHS = ("/docs", "/redoc")
API_PATHS = ("/api", "/health", "/openapi.json")

COMMON_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
}


def _matches(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == p or path.startswith(p + "/") for p in prefixes)


def csp_for_path(path: str, extra_connect_src: list[str] | None = None) -> str:
    if _matches(path, DOCS_PATHS):
        return DOCS_CSP
    if _matches(path, API_PATHS):
        return API_CSP
    extra = "".join(f" {src}" for src in (extra_connect_src or []))
    return SPA_CSP.format(extra_connect=extra)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, extra_connect_src: list[str] | None = None) -> None:
        self.app = app
        self.extra_connect_src = [s for s in (extra_connect_src or []) if s]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        csp = csp_for_path(scope.get("path", ""), self.extra_connect_src)

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                # Do not override a header a route set on purpose.
                if "content-security-policy" not in headers:
                    headers["Content-Security-Policy"] = csp
                for name, value in COMMON_HEADERS.items():
                    if name.lower() not in headers:
                        headers[name] = value
            await send(message)

        await self.app(scope, receive, send_with_headers)
