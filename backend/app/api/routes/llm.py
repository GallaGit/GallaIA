"""F2.1b — LLM gateway status + usage log (read-only)."""

from fastapi import APIRouter, Query

from app.api.dependencies.db import DbSession
from app.llm import gateway
from app.llm.usage import list_usage, usage_out, usage_summary

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/usage")
def api_llm_usage(
    db: DbSession,
    limit: int = Query(50, ge=1, le=500),
):
    """Recent gateway calls (newest first) + totals per provider/model.

    Never includes prompts, responses or API keys.
    """
    return {
        "backend": gateway.llm_backend(),
        "providers": [p.name for p in gateway.configured_providers()],
        "summary": usage_summary(db),
        "recent": [usage_out(row) for row in list_usage(db, limit=limit)],
    }
