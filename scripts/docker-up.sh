#!/usr/bin/env bash
# Build frontend + one-container Docker app (from repo root).
set -euo pipefail
cd "$(dirname "$0")/.."
test -f backend/.env || cp backend/.env.example backend/.env
npm --prefix frontend ci --no-audit --no-fund
npm --prefix frontend run build
docker compose up --build "$@"
