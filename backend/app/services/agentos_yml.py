"""Export / import agentos.yml + CLI create/update (Phase 6).

Lean projection of agents + templates. Idempotent apply by agent.name /
template.slug within a project. create_agent / update_agent share the same
row shape as import so CLI and UI/API list the same agents.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.exceptions import BadRequestError, NotFoundError
from app.models import Agent, Project
from app.models.template import TaskTemplate, TaskTemplateStep
from app.schemas.agentos_yml import (
    AgentOsImportResult,
    AgentOsYml,
    AgentYml,
    TemplateStepYml,
    TemplateYml,
)


def _require_project(db: Session, project_slug: str = "default") -> Project:
    project = db.scalar(select(Project).where(Project.slug == project_slug))
    if project is None:
        raise NotFoundError(f"Project slug={project_slug!r} not found")
    return project


def _get_agent_by_name(
    db: Session, project: Project, name: str
) -> Agent | None:
    return db.scalar(
        select(Agent).where(Agent.project_id == project.id, Agent.name == name)
    )


def export_agentos_yml(
    db: Session, *, project_slug: str = "default"
) -> AgentOsYml:
    """Serialize agents + templates for a project into the YAML schema."""
    project = _require_project(db, project_slug)

    agents = list(
        db.scalars(
            select(Agent)
            .where(Agent.project_id == project.id)
            .order_by(Agent.name)
        ).all()
    )
    templates = list(
        db.scalars(
            select(TaskTemplate)
            .options(selectinload(TaskTemplate.steps))
            .where(TaskTemplate.project_id == project.id)
            .order_by(TaskTemplate.slug)
        ).all()
    )

    return AgentOsYml(
        version=1,
        agents=[
            AgentYml(
                name=a.name,
                title=a.title,
                model=a.model,
                foundational_prompt=a.foundational_prompt,
                role_prompt=a.role_prompt,
                runner_preference=a.runner_preference,
            )
            for a in agents
        ],
        templates=[
            TemplateYml(
                slug=t.slug,
                name=t.name,
                description=t.description,
                steps=[
                    TemplateStepYml(
                        position=s.position,
                        name=s.name,
                        description=s.description,
                        assignee_agent_name=s.assignee_agent_name,
                        approval_gate=s.approval_gate,
                        requires_previous_done=s.requires_previous_done,
                    )
                    for s in sorted(t.steps, key=lambda x: x.position)
                ],
            )
            for t in templates
        ],
    )


def agentos_yml_to_dict(doc: AgentOsYml) -> dict[str, Any]:
    """Stable dict suitable for yaml.safe_dump (omit None on templates/steps)."""
    return doc.model_dump(mode="python", exclude_none=True)


def dump_agentos_yml(doc: AgentOsYml) -> str:
    """Render agentos.yml text (UTF-8)."""
    return yaml.safe_dump(
        agentos_yml_to_dict(doc),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )


def parse_agentos_yml(raw: str | dict[str, Any]) -> AgentOsYml:
    """Parse and validate YAML text or a pre-loaded dict."""
    if isinstance(raw, str):
        data = yaml.safe_load(raw)
    else:
        data = raw
    if data is None:
        raise BadRequestError("agentos.yml is empty")
    if not isinstance(data, dict):
        raise BadRequestError("agentos.yml root must be a mapping")
    try:
        return AgentOsYml.model_validate(data)
    except Exception as exc:  # noqa: BLE001 — surface as BadRequest
        raise BadRequestError(f"Invalid agentos.yml: {exc}") from exc


def load_agentos_yml(path: Path | str) -> AgentOsYml:
    text = Path(path).read_text(encoding="utf-8")
    return parse_agentos_yml(text)


def write_agentos_yml(path: Path | str, doc: AgentOsYml) -> None:
    Path(path).write_text(dump_agentos_yml(doc), encoding="utf-8")


def parse_agent_yml_snippet(raw: str | dict[str, Any]) -> AgentYml:
    """Parse a single-agent YAML snippet or a mini agentos.yml with one agent.

    Accepts:
      - a bare agent mapping: {name, title, ...}
      - {agents: [{...}]} (uses first entry)
      - full AgentOsYml (uses first agent)
    """
    if isinstance(raw, str):
        data = yaml.safe_load(raw)
    else:
        data = raw
    if data is None:
        raise BadRequestError("agent YAML snippet is empty")
    if not isinstance(data, dict):
        raise BadRequestError("agent YAML snippet must be a mapping")
    if "agents" in data:
        doc = parse_agentos_yml(data)
        if not doc.agents:
            raise BadRequestError("agent YAML snippet has empty agents list")
        return doc.agents[0]
    if "name" in data:
        try:
            return AgentYml.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            raise BadRequestError(f"Invalid agent YAML: {exc}") from exc
    raise BadRequestError(
        "agent YAML snippet needs 'name' or an 'agents' list"
    )


def parse_template_yml_snippet(raw: str | dict[str, Any]) -> TemplateYml:
    """Parse a single-template YAML snippet or mini agentos.yml with one template."""
    if isinstance(raw, str):
        data = yaml.safe_load(raw)
    else:
        data = raw
    if data is None:
        raise BadRequestError("template YAML snippet is empty")
    if not isinstance(data, dict):
        raise BadRequestError("template YAML snippet must be a mapping")
    if "templates" in data:
        doc = parse_agentos_yml(data)
        if not doc.templates:
            raise BadRequestError("template YAML snippet has empty templates list")
        return doc.templates[0]
    if "slug" in data:
        try:
            return TemplateYml.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            raise BadRequestError(f"Invalid template YAML: {exc}") from exc
    raise BadRequestError(
        "template YAML snippet needs 'slug' or a 'templates' list"
    )


def create_agent(
    db: Session,
    *,
    name: str,
    title: str | None = None,
    role_prompt: str = "",
    model: str = "claude-sonnet-4",
    foundational_prompt: str = "",
    runner_preference: str = "mock",
    project_slug: str = "default",
    commit: bool = True,
) -> Agent:
    """Create an agent row (same shape as YAML import / GET /api/v1/agents)."""
    project = _require_project(db, project_slug)
    if _get_agent_by_name(db, project, name) is not None:
        raise BadRequestError(f"Agent name={name!r} already exists")

    entry = AgentYml(
        name=name,
        title=title if title else name,
        model=model,
        foundational_prompt=foundational_prompt,
        role_prompt=role_prompt,
        runner_preference=runner_preference,
    )
    agent = Agent(
        project_id=project.id,
        name=entry.name,
        title=entry.title,
        model=entry.model,
        foundational_prompt=entry.foundational_prompt,
        role_prompt=entry.role_prompt,
        runner_preference=entry.runner_preference,
    )
    db.add(agent)
    if commit:
        db.commit()
        db.refresh(agent)
    else:
        db.flush()
    return agent


def create_agent_from_yml(
    db: Session,
    entry: AgentYml,
    *,
    project_slug: str = "default",
    commit: bool = True,
) -> Agent:
    """Create from a validated AgentYml (fails if name exists)."""
    return create_agent(
        db,
        name=entry.name,
        title=entry.title,
        role_prompt=entry.role_prompt,
        model=entry.model,
        foundational_prompt=entry.foundational_prompt,
        runner_preference=entry.runner_preference,
        project_slug=project_slug,
        commit=commit,
    )


def update_agent(
    db: Session,
    *,
    name: str,
    title: str | None = None,
    role_prompt: str | None = None,
    model: str | None = None,
    foundational_prompt: str | None = None,
    runner_preference: str | None = None,
    project_slug: str = "default",
    commit: bool = True,
) -> Agent:
    """Partial update by agent name (same fields as YAML import / UI)."""
    project = _require_project(db, project_slug)
    agent = _get_agent_by_name(db, project, name)
    if agent is None:
        raise NotFoundError(f"Agent name={name!r} not found")

    if title is not None:
        agent.title = title
    if role_prompt is not None:
        agent.role_prompt = role_prompt
    if model is not None:
        agent.model = model
    if foundational_prompt is not None:
        agent.foundational_prompt = foundational_prompt
    if runner_preference is not None:
        agent.runner_preference = runner_preference

    if commit:
        db.commit()
        db.refresh(agent)
    else:
        db.flush()
    return agent


def create_template(
    db: Session,
    entry: TemplateYml,
    *,
    project_slug: str = "default",
    commit: bool = True,
) -> TaskTemplate:
    """Create a template (fails if slug exists). Prefer import for bulk."""
    project = _require_project(db, project_slug)
    existing = db.scalar(
        select(TaskTemplate).where(TaskTemplate.slug == entry.slug)
    )
    if existing is not None:
        raise BadRequestError(f"Template slug={entry.slug!r} already exists")

    template = TaskTemplate(
        project_id=project.id,
        slug=entry.slug,
        name=entry.name,
        description=entry.description,
    )
    db.add(template)
    db.flush()
    for step in sorted(entry.steps, key=lambda s: s.position):
        db.add(
            TaskTemplateStep(
                template_id=template.id,
                position=step.position,
                name=step.name,
                description=step.description,
                assignee_agent_name=step.assignee_agent_name,
                approval_gate=step.approval_gate,
                requires_previous_done=step.requires_previous_done,
            )
        )
    if commit:
        db.commit()
        db.refresh(template)
    else:
        db.flush()
    return template


def _upsert_agent(
    db: Session, project: Project, entry: AgentYml, result: AgentOsImportResult
) -> None:
    existing = _get_agent_by_name(db, project, entry.name)
    if existing is None:
        db.add(
            Agent(
                project_id=project.id,
                name=entry.name,
                title=entry.title,
                model=entry.model,
                foundational_prompt=entry.foundational_prompt,
                role_prompt=entry.role_prompt,
                runner_preference=entry.runner_preference,
            )
        )
        result.agents_created += 1
        return

    existing.title = entry.title
    existing.model = entry.model
    existing.foundational_prompt = entry.foundational_prompt
    existing.role_prompt = entry.role_prompt
    existing.runner_preference = entry.runner_preference
    result.agents_updated += 1


def _upsert_template(
    db: Session, project: Project, entry: TemplateYml, result: AgentOsImportResult
) -> None:
    existing = db.scalar(
        select(TaskTemplate)
        .options(selectinload(TaskTemplate.steps))
        .where(TaskTemplate.slug == entry.slug)
    )
    steps_sorted = sorted(entry.steps, key=lambda s: s.position)

    if existing is None:
        template = TaskTemplate(
            project_id=project.id,
            slug=entry.slug,
            name=entry.name,
            description=entry.description,
        )
        db.add(template)
        db.flush()
        for step in steps_sorted:
            db.add(
                TaskTemplateStep(
                    template_id=template.id,
                    position=step.position,
                    name=step.name,
                    description=step.description,
                    assignee_agent_name=step.assignee_agent_name,
                    approval_gate=step.approval_gate,
                    requires_previous_done=step.requires_previous_done,
                )
            )
        result.templates_created += 1
        return

    # Slug may already exist on another project — keep lean: only update if same project.
    if existing.project_id != project.id:
        raise BadRequestError(
            f"Template slug={entry.slug!r} belongs to another project"
        )

    existing.name = entry.name
    existing.description = entry.description
    # Replace steps for idempotent apply.
    for old in list(existing.steps):
        db.delete(old)
    db.flush()
    for step in steps_sorted:
        db.add(
            TaskTemplateStep(
                template_id=existing.id,
                position=step.position,
                name=step.name,
                description=step.description,
                assignee_agent_name=step.assignee_agent_name,
                approval_gate=step.approval_gate,
                requires_previous_done=step.requires_previous_done,
            )
        )
    result.templates_updated += 1


def import_agentos_yml(
    db: Session,
    doc: AgentOsYml,
    *,
    project_slug: str = "default",
    commit: bool = True,
) -> AgentOsImportResult:
    """Create/update agents (by name) and templates (by slug). Idempotent."""
    if doc.version != 1:
        raise BadRequestError(f"Unsupported agentos.yml version: {doc.version}")

    project = _require_project(db, project_slug)
    result = AgentOsImportResult()

    for agent in doc.agents:
        _upsert_agent(db, project, agent, result)
    for template in doc.templates:
        _upsert_template(db, project, template, result)

    if commit:
        db.commit()
    else:
        db.flush()
    return result
