# GallaIA AgentOS frontend

React + Vite + TypeScript control-plane UI (atelier theme).
Cross-platform web app: Windows / Linux / macOS browsers.

## Setup

cd frontend
npm install

## Dev

npm run dev

Opens http://127.0.0.1:5173/ and proxies /api to FastAPI on port 8000.
Optional: copy .env.example to .env and set VITE_API_URL.

## Build

```bash
npm run build
```

Salida en `dist/`. Ese artefacto lo copia el `Dockerfile` de la raíz a `/app/static` para el contenedor único (UI + API en http://127.0.0.1:8000/). Ver [docs/deployment/docker.md](../docs/deployment/docker.md).

## Routes

Agents, Tasks (Kanban), Sessions, Inbox, Files (placeholder), Settings (placeholder).
