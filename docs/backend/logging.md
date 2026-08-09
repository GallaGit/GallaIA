# Logging

## Purpose

Describe the logging setup so local runs and Docker share a consistent, readable format without leaking secrets.

## Status

Draft (reflects current implementation)

## Scope

- Existing: `app/core/logging.py` (`setup_logging`, `get_logger`); called from `main.py` using `settings.log_level`; startup/shutdown logs in lifespan; debug logs on `/` and `/health`.
- Planned: request-id correlation, structured JSON for production if needed.
- Future: log shipping / metrics / tracing.

## How it works

1. `setup_logging(level)` configures root logging once (`basicConfig`, `force=True` so uvicorn does not swallow the format).
2. Format: `%(asctime)s | %(levelname)s | %(name)s | %(message)s` to stdout.
3. Modules obtain loggers with `get_logger(__name__)`.

## Usage today

- Lifespan logs app name, env, and debug flag at startup; shutdown message on stop.
- Endpoint handlers may log at `DEBUG` (visible when `LOG_LEVEL=DEBUG`).

## Code

- [`backend/app/core/logging.py`](../../backend/app/core/logging.py)
- [`backend/app/main.py`](../../backend/app/main.py)

## TODO

- Redaction guidelines when logging request bodies or provider payloads.
- Align production format with deployment docs when those exist.
