# Logging

## Purpose

Establish why structured logging matters for an AI-backed API, and how logging will be configured without leaking secrets or prompt contents inappropriately.

## Status

Draft

## Scope

- Existing: Empty `app/core/logging.py`.
- Planned: Central logging setup, log levels via config, request-correlated logs for Temporada 1.
- Future: Centralized log shipping, metrics, and tracing.

## TODO

- Choose log format (JSON vs text) for local vs container runs.
- Define fields to include (timestamp, level, request id, route) and fields to redact.
- Document logger acquisition conventions (`getLogger(__name__)` or project helper).
- Align with `configuration.md` for log-level settings.
