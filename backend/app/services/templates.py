"""TaskTemplate seed, list/get, instantiate, and prior-step gate."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.exceptions import BadRequestError, NotFoundError
from app.models import Agent, Project, Task
from app.models.template import TaskTemplate, TaskTemplateStep
from app.schemas.task import TaskOut
from app.schemas.template import TemplateInstantiateOut, TemplateOut

DEMO_TWO_STEP_SLUG = "demo-two-step"
COMPOUND_ENGINEER_SLUG = "compound-engineer-workflow"

# Phase 3 sketch (POSTMA_WALKTHROUGH §2.8): N+1 gated on N done.
_COMPOUND_STEPS: tuple[tuple[int, str, str, str | None, bool, bool], ...] = (
    # position, name, description, assignee_agent_name, approval_gate, requires_previous_done
    (
        1,
        "Escribir spec",
        "Draft feature spec (human approval gate). Typical variable: branchName.",
        "spec",
        True,
        False,
    ),
    (
        2,
        "Plan",
        "Write implementation plan; notify via inbox/activity.",
        "plan",
        False,
        True,
    ),
    (
        3,
        "Plan review",
        "Coordinator spawns plan reviewers (feasibility, scope, coherence, risk).",
        "review-coordinator",
        False,
        True,
    ),
    (
        4,
        "Revisar plan",
        "Plan agent revises plan from review feedback.",
        "plan",
        False,
        True,
    ),
    (
        5,
        "Implementacion + E2E",
        "Implement feature and run E2E inside the workflow.",
        "implementation-plan-executioner",
        False,
        True,
    ),
    (
        6,
        "Code review",
        "Coordinator-driven code review of the implementation.",
        "review-coordinator",
        False,
        True,
    ),
    (
        7,
        "Aplicar fixes",
        "Senior-dev applies review fixes.",
        "senior-dev",
        False,
        True,
    ),
    (
        8,
        "Wiki",
        "Librarian updates product wiki / knowledge.",
        "librarian",
        False,
        True,
    ),
    (
        9,
        "Review humano del PR",
        "Human merge gate on the final PR.",
        "human",
        True,
        True,
    ),
)


def _seed_demo_two_step(db: Session, project_id: int) -> bool:
    existing = db.scalar(
        select(TaskTemplate).where(TaskTemplate.slug == DEMO_TWO_STEP_SLUG)
    )
    if existing is not None:
        return False

    template = TaskTemplate(
        project_id=project_id,
        slug=DEMO_TWO_STEP_SLUG,
        name="Demo two-step workflow",
        description=(
            "Lean Phase 3 seed: step 1 has an approval gate; "
            "step 2 cannot start/run until step 1 is done."
        ),
    )
    db.add(template)
    db.flush()
    db.add_all(
        [
            TaskTemplateStep(
                template_id=template.id,
                position=1,
                name="Draft plan",
                description="Human-reviewed first step (approval gate).",
                assignee_agent_name="plan",
                approval_gate=True,
                requires_previous_done=False,
            ),
            TaskTemplateStep(
                template_id=template.id,
                position=2,
                name="Implement",
                description="Blocked until step 1 is marked done.",
                assignee_agent_name="senior-dev",
                approval_gate=False,
                requires_previous_done=True,
            ),
        ]
    )
    return True


def _seed_compound_engineer(db: Session, project_id: int) -> bool:
    existing = db.scalar(
        select(TaskTemplate).where(TaskTemplate.slug == COMPOUND_ENGINEER_SLUG)
    )
    if existing is not None:
        return False

    template = TaskTemplate(
        project_id=project_id,
        slug=COMPOUND_ENGINEER_SLUG,
        name="Compound engineer workflow",
        description=(
            "Phase 3 seed: 9-step feature build (POSTMA 2.8). "
            "Each step after 1 is gated on the previous done. "
            "Gates on steps 1 and 9 (human approve/merge)."
        ),
    )
    db.add(template)
    db.flush()
    db.add_all(
        [
            TaskTemplateStep(
                template_id=template.id,
                position=pos,
                name=name,
                description=desc,
                assignee_agent_name=assignee,
                approval_gate=gate,
                requires_previous_done=req_prev,
            )
            for pos, name, desc, assignee, gate, req_prev in _COMPOUND_STEPS
        ]
    )
    return True


def ensure_seed_templates(db: Session) -> None:
    """Idempotent Phase 3 seeds: demo-two-step + compound-engineer-workflow."""
    project = db.scalar(select(Project).where(Project.slug == "default"))
    if project is None:
        return

    dirty = False
    dirty = _seed_demo_two_step(db, project.id) or dirty
    dirty = _seed_compound_engineer(db, project.id) or dirty
    if dirty:
        db.commit()


def _load_template(db: Session, template_id: int | None = None, slug: str | None = None) -> TaskTemplate:
    stmt = select(TaskTemplate).options(selectinload(TaskTemplate.steps))
    if template_id is not None:
        stmt = stmt.where(TaskTemplate.id == template_id)
    elif slug is not None:
        stmt = stmt.where(TaskTemplate.slug == slug)
    else:
        raise BadRequestError("template id or slug required")
    template = db.scalar(stmt)
    if template is None:
        key = template_id if template_id is not None else slug
        raise NotFoundError(f"Template {key} not found")
    return template


def list_templates(db: Session, project_id: int | None = None) -> list[TaskTemplate]:
    stmt = (
        select(TaskTemplate)
        .options(selectinload(TaskTemplate.steps))
        .order_by(TaskTemplate.id)
    )
    if project_id is not None:
        stmt = stmt.where(TaskTemplate.project_id == project_id)
    return list(db.scalars(stmt).all())


def get_template(db: Session, key: str) -> TaskTemplate:
    """Resolve by numeric id or slug."""
    if key.isdigit():
        return _load_template(db, template_id=int(key))
    return _load_template(db, slug=key)


def template_out(template: TaskTemplate) -> TemplateOut:
    return TemplateOut.model_validate(template)


def _resolve_assignee(db: Session, project_id: int, agent_name: str | None) -> int | None:
    if not agent_name:
        return None
    agent = db.scalar(
        select(Agent).where(Agent.project_id == project_id, Agent.name == agent_name)
    )
    return agent.id if agent is not None else None


def instantiate_template(
    db: Session,
    template: TaskTemplate,
    *,
    project_id: int | None = None,
    name_prefix: str | None = None,
) -> TemplateInstantiateOut:
    """Create one task card per step; wire depends_on for gated steps."""
    steps = sorted(template.steps, key=lambda s: s.position)
    if not steps:
        raise BadRequestError("Template has no steps")

    pid = project_id or template.project_id
    if db.get(Project, pid) is None:
        raise NotFoundError(f"Project {pid} not found")

    run_id = str(uuid.uuid4())
    prefix = (name_prefix or "").strip()
    created: list[Task] = []
    by_position: dict[int, Task] = {}

    for step in steps:
        title = f"{prefix}{step.name}" if prefix else step.name
        depends_on_id = None
        if step.requires_previous_done:
            prior = by_position.get(step.position - 1)
            if prior is None:
                raise BadRequestError(
                    f"Step {step.position} requires previous done but prior step missing"
                )
            depends_on_id = prior.id

        task = Task(
            project_id=pid,
            name=title,
            description=step.description,
            status="todo",
            assignee_agent_id=_resolve_assignee(db, pid, step.assignee_agent_name),
            approval_gate=step.approval_gate,
            template_id=template.id,
            template_run_id=run_id,
            step_index=step.position,
            depends_on_task_id=depends_on_id,
        )
        db.add(task)
        db.flush()
        by_position[step.position] = task
        created.append(task)

    db.commit()
    for task in created:
        db.refresh(task)

    return TemplateInstantiateOut(
        template_id=template.id,
        template_slug=template.slug,
        run_id=run_id,
        tasks=[TaskOut.model_validate(t) for t in created],
    )


def assert_prior_step_done(db: Session, task: Task) -> None:
    """Enforce approval/dependency gate: blocked until depends_on task is done."""
    if task.depends_on_task_id is None:
        return
    prior = db.get(Task, task.depends_on_task_id)
    if prior is None:
        raise BadRequestError(
            f"Task #{task.id} depends on missing task #{task.depends_on_task_id}"
        )
    if prior.status != "done":
        raise BadRequestError(
            f"Step {task.step_index} blocked until step "
            f"{prior.step_index or '?'} (task #{prior.id}) is done "
            f"(current status={prior.status!r})"
        )


def seed_template_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(TaskTemplate)) or 0
