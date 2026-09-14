"""Minimal agentos.yml schema (Phase 6 slice 1): agents + templates."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AgentYml(BaseModel):
    """One agent entry in agentos.yml (idempotent key: name)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    model: str = Field(default="claude-sonnet-4", max_length=80)
    foundational_prompt: str = ""
    role_prompt: str = ""
    runner_preference: str = Field(default="mock", max_length=20)


class TemplateStepYml(BaseModel):
    """One ordered step under a template."""

    model_config = ConfigDict(extra="forbid")

    position: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    assignee_agent_name: str | None = Field(default=None, max_length=80)
    approval_gate: bool = False
    requires_previous_done: bool = False


class TemplateYml(BaseModel):
    """One task template (idempotent key: slug)."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    steps: list[TemplateStepYml] = Field(default_factory=list)


class AgentOsYml(BaseModel):
    """Root document for agentos.yml (version 1)."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    agents: list[AgentYml] = Field(default_factory=list)
    templates: list[TemplateYml] = Field(default_factory=list)


class AgentOsImportResult(BaseModel):
    """Summary of an import/apply pass."""

    agents_created: int = 0
    agents_updated: int = 0
    templates_created: int = 0
    templates_updated: int = 0
