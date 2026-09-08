from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    title: str
    model: str
    foundational_prompt: str = Field(
        description="RECONSTRUCTED from AgentOS talk — not verbatim"
    )
    role_prompt: str = Field(description="RECONSTRUCTED from AgentOS talk — not verbatim")
    runner_preference: str
    created_at: datetime
    prompts_note: str = "RECONSTRUCTED from Danny Postma's AgentOS talk — not his verbatim prompts."
