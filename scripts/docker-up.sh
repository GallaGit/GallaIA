#!/usr/bin/env bash
# Build frontend + one-container Docker app (from repo root).
set -euo pipefail
cd "$(dirname "$0")/.."
test -f backend/.env || cp backend/.env.example backend/.env
# GALLAIA-SEC-002: the backend refuses to start without an operator token.
if ! grep -Eq '^GALLAIA_OPERATOR_TOKEN=.{32,}' backend/.env; then
  echo "ERROR: set GALLAIA_OPERATOR_TOKEN (>=32 chars) in backend/.env first:" >&2
  echo '  python -c "import secrets;print(secrets.token_urlsafe(32))"' >&2
  exit 1
fi
npm --prefix frontend ci --no-audit --no-fund
npm --prefix frontend run build
docker compose up --build "$@"
