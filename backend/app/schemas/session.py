from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
import json


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    task_id: int | None = None
    runner: str
    status: str
    tool_call_log: list[Any] = Field(default_factory=list)
    summary: str | None = None
    started_at: datetime
    ended_at: datetime | None = None

    @field_validator("tool_call_log", mode="before")
    @classmethod
    def parse_tool_log(cls, v: Any) -> list:
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return []
