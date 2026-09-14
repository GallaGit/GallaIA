from pydantic import BaseModel, Field
from typing import Literal

GrantKind = Literal["mcp", "repo", "env"]


class GrantItem(BaseModel):
    kind: GrantKind
    name: str = Field(min_length=1, max_length=200)


class AgentGrantsOut(BaseModel):
    agent_id: int | None = None
    agent_name: str
    grants: list[GrantItem]


class AgentGrantsUpdate(BaseModel):
    grants: list[GrantItem]
