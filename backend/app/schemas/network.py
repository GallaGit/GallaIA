from pydantic import BaseModel, Field
from typing import Literal

NetworkMode = Literal["open", "limited"]


class AgentNetworkOut(BaseModel):
    agent_id: int | None = None
    agent_name: str
    mode: NetworkMode
    allowlist: list[str] = Field(default_factory=list)


class AgentNetworkUpdate(BaseModel):
    mode: NetworkMode
    allowlist: list[str] = Field(default_factory=list)
