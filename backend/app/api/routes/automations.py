"""Named automations CRUD + test-clock tick."""

from fastapi import APIRouter

from app.api.dependencies.db import DbSession
from app.schemas.automation import (
    AutomationCreate,
    AutomationOut,
    AutomationTickIn,
    AutomationTickOut,
    AutomationUpdate,
)
from app.services.automations import (
    automation_out,
    create_automation,
    delete_automation,
    get_automation,
    list_automations,
    tick_automations,
    update_automation,
)

router = APIRouter(prefix="/automations", tags=["automations"])


@router.get("", response_model=list[AutomationOut])
def api_list_automations(db: DbSession):
    return [automation_out(a) for a in list_automations(db)]


@router.post("/tick", response_model=AutomationTickOut)
def api_tick_automations(db: DbSession, payload: AutomationTickIn | None = None):
    """Fire due automations. Optional now for a test clock."""
    body = payload or AutomationTickIn()
    return tick_automations(db, now=body.now)


@router.post("", response_model=AutomationOut, status_code=201)
def api_create_automation(payload: AutomationCreate, db: DbSession):
    return automation_out(create_automation(db, payload))


@router.get("/{automation_id}", response_model=AutomationOut)
def api_get_automation(automation_id: int, db: DbSession):
    return automation_out(get_automation(db, automation_id))


@router.patch("/{automation_id}", response_model=AutomationOut)
def api_update_automation(automation_id: int, payload: AutomationUpdate, db: DbSession):
    return automation_out(update_automation(db, automation_id, payload))


@router.delete("/{automation_id}", status_code=204)
def api_delete_automation(automation_id: int, db: DbSession):
    delete_automation(db, automation_id)
