from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal

SecretProvider = Literal["env"]


class SecretRefItem(BaseModel):
    """Pointer only — extra fields such as `value` are rejected."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=64)
    provider: SecretProvider = "env"
    key: str = Field(default="", max_length=64)

    @model_validator(mode="after")
    def default_key(self) -> "SecretRefItem":
        if not (self.key or "").strip():
            self.key = self.name.strip()
        return self


class AgentSecretsOut(BaseModel):
    agent_id: int | None = None
    agent_name: str
    secrets: list[SecretRefItem] = Field(default_factory=list)


class AgentSecretsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    secrets: list[SecretRefItem] = Field(default_factory=list)
