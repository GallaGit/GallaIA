# GallaAI — single image: Vite UI + FastAPI (SQLite)
# From repo root:
#   npm --prefix frontend ci && npm --prefix frontend run build
#   docker compose up --build
#
# (npm inside Docker BuildKit fails on some Windows/proxy setups;
#  the runtime is still one container with UI + API.)

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STATIC_DIR=/app/static

# GALLAIA-SEC-005: install the exact, hash-pinned dependency set (direct and
# transitive). --no-deps: nothing outside the lockfile can be pulled in.
# Regenerate with `uv pip compile` (see backend/README.md) after editing pyproject.toml.
COPY backend/requirements.lock .
RUN pip install --no-cache-dir --require-hashes --no-deps -r requirements.lock

# The app runs from /app (uvicorn app.main:app); it does not need to be pip-installed.
COPY backend/app ./app

# Pre-built by Vite on the host (see comment above)
COPY frontend/dist ./static

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

# Listens on 0.0.0.0 inside the container only; docker-compose publishes it on
# 127.0.0.1:8000 of the host (GALLAIA-SEC-003). With `docker run`, use
# `-p 127.0.0.1:8000:8000`.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
