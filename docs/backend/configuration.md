# Configuration

## Purpose

Explain how application settings are loaded from the environment, why they are centralized, and which variables exist today.

## Status

Draft (reflects current implementation)

## Scope

- Existing: `app/core/config.py` (`Settings` via pydantic-settings), `backend/.env`, `backend/.env.example`, injection via `get_settings()` (also used from Docker Compose `env_file`); `OPENROUTER_*` (Chat Completions; primary LLM provider, implemented in `backend/app/providers/openrouter.py`) and `ANTHROPIC_*` (Messages stub; legacy/optional, not the intended provider, to be removed/replaced in a later code PR). Groq is the planned fallback provider (not implemented yet; a `GROQ_API_KEY` variable is planned). Provider routing via LiteLLM is planned for F2+.

> Note: free OpenRouter models have low rate limits and can disappear without notice, so always configure a fallback model.
- Existing: Phase 5 webhook secret `GALLAIA_WEBHOOK_SECRET`.
- Planned: richer runner / cron settings — [ROADMAP.md](../ROADMAP.md).
- Future: multi-environment profiles; Postgres URL when ADR-003 is accepted.
## How it works

1. `Settings` subclasses `BaseSettings` and reads `backend/.env` when the process cwd is `backend/` (as with `uvicorn` / Compose).
2. Env names map to fields: `APP_NAME` → `app_name`, etc.
3. `get_settings()` is cached with `@lru_cache` (one instance per process). After changing `.env`, restart the process.

## Variables (current)

| Env var | Field | Default / role |
|---------|-------|----------------|
| `APP_NAME` | `app_name` | Display name / OpenAPI title |
| `APP_ENV` | `app_env` | e.g. `development` |
| `APP_DEBUG` | `app_debug` | Debug flag |
| `LOG_LEVEL` | `log_level` | Logging level (`INFO`, `DEBUG`, …) |
| `ANTHROPIC_API_KEY` | `anthropic_api_key` | Legacy/optional, to be removed. Messages stub; empty → skip Anthropic |
| `ANTHROPIC_MODEL` | `anthropic_model` | Legacy/optional, to be removed. Default `claude-sonnet-4-5` |
| `OPENROUTER_API_KEY` | `openrouter_api_key` | Primary provider (Chat Completions); empty → skip OpenRouter |
| `OPENROUTER_MODEL` | `openrouter_model` | Default `nvidia/nemotron-3-ultra-550b-a55b:free` |
| `OPENROUTER_BASE_URL` | `openrouter_base_url` | Default `https://openrouter.ai/api/v1` |
| `CORS_ORIGINS` | `cors_origins` | Comma-separated browser origins (no `*`). Also used by the SEC-011 Origin guard: POST/PUT/PATCH/DELETE on `/api/v1` with an `Origin` not listed (and not same-origin) → 403; missing `Origin` allowed; `/api/v1/triggers` exempt |
| `ALLOWED_HOSTS` | `allowed_hosts` | GALLAIA-SEC-011 `TrustedHostMiddleware` allow-list; default `localhost,127.0.0.1,testserver`. Other `Host` → 400 |
| `CSP_EXTRA_CONNECT_SRC` | `csp_extra_connect_src` | GALLAIA-SEC-007: extra origins (comma-separated) for the SPA CSP `connect-src`. Empty by default; only needed if the UI is built with `VITE_API_URL` pointing to another origin |
| `GALLAIA_WEBHOOK_SECRET` | `gallaia_webhook_secret` | Phase 5 public webhook; empty → 401 |

## Security headers (GALLAIA-SEC-007)

`SecurityHeadersMiddleware` (`backend/app/middleware/security_headers.py`) adds to every response:
`Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy: no-referrer`, `Cross-Origin-Opener-Policy: same-origin` and a restrictive `Permissions-Policy`.

| Paths | CSP |
|-------|-----|
| SPA (`/`, client routes, `/assets`, `sw.js`…) | `default-src 'self'`; scripts only `'self'`; styles/fonts also from Google Fonts; `connect-src 'self'` (API + SSE); `frame-ancestors 'none'` |
| `/api/*`, `/health`, `/openapi.json` | `default-src 'none'; frame-ancestors 'none'` |
| `/docs`, `/redoc` (off in production) | Relaxed (inline script + jsDelivr) so Swagger UI / ReDoc keep working |

It is pure ASGI (does not buffer SSE) and never overrides a header set by a route. In dev
(`npm run dev`) the page comes from Vite, so only the proxied `/api` responses carry these headers.
No HSTS: the app is served over plain HTTP on localhost.

## Conventions

- Commit `.env.example` only. Never commit real secrets in `.env`.
- Prefer reading config through `Settings` / `Depends(get_settings)`, not scattered `os.getenv` calls.

## Code

- [`backend/app/core/config.py`](../../backend/app/core/config.py)
- Runbook: [`backend/README.md`](../../backend/README.md)

## TODO

- Document new settings as AgentOS phases add Isolation secrets / runners; Postgres URL only when ADR-003 lands.
