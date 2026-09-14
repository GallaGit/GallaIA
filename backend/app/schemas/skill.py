from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str | None = None
    kind: str
    body: str
    created_at: datetime
    updated_at: datetime


class SkillCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    kind: str = Field(default="prompt", pattern=r"^(prompt|file)$")
    body: str = ""


class SkillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    kind: str | None = Field(default=None, pattern=r"^(prompt|file)$")
    body: str | None = None


class SkillUpsert(BaseModel):
    """PUT body: create or replace by slug (slug comes from path)."""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    kind: str = Field(default="prompt", pattern=r"^(prompt|file)$")
    body: str = ""
