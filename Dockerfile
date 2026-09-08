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
    PIP_TRUSTED_HOST="pypi.org files.pythonhosted.org pypi.python.org" \
    STATIC_DIR=/app/static

COPY backend/pyproject.toml .
COPY backend/app ./app

RUN pip install --no-cache-dir .

# Pre-built by Vite on the host (see comment above)
COPY frontend/dist ./static

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
