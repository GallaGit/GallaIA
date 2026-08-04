# Configuration

## Purpose

Capture why configuration is centralized in `app/core/config.py`, how environment variables will be loaded, and how secrets stay out of source control.

## Status

Draft

## Scope

- Existing: Empty `app/core/config.py` and empty `backend/.env.example`.
- Planned: Settings model (e.g. pydantic-settings), env loading, and documented variables for Temporada 1.
- Future: Multi-environment profiles and secrets management beyond local `.env`.

## TODO

- Define required vs optional settings for Temporada 1 (API keys, app env, log level).
- Document `.env` / `.env.example` conventions and what never gets committed.
- Explain how config is injected into the app (no global mutable state).
- Align with empty Docker/compose files when they are filled.
