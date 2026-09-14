from fastapi import APIRouter

from app.api.routes import (
    agentos,
    agents,
    health,
    inbox,
    projects,
    scheduler,
    sessions,
    goals,
    skills,
    tasks,
    templates,
    triggers,
    automations,
    activity,
    runners,
)

api_router = APIRouter()
api_router.include_router(health.router)

# Primary SQLAlchemy control-plane (used by frontend atelier UI)
api_router.include_router(projects.router)
api_router.include_router(agents.router)
api_router.include_router(tasks.router)
api_router.include_router(templates.router)
api_router.include_router(skills.router)
api_router.include_router(goals.router)
api_router.include_router(sessions.router)
api_router.include_router(inbox.router)
api_router.include_router(scheduler.router)
api_router.include_router(triggers.router)
api_router.include_router(automations.router)
api_router.include_router(activity.router)
api_router.include_router(runners.router)

# Teammate in-memory AgentOS module (contract: /api/v1/agentos/*)
api_router.include_router(agentos.router)
