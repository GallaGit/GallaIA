"""F1.1 thread/message schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ThreadStatus = Literal["open", "closed"]
MessageKind = Literal["text", "delegation", "result"]


class ThreadCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    project_id: int | None = None
    created_by: str = Field(default="user", min_length=1, max_length=80)


class ThreadUpdate(BaseModel):
    status: ThreadStatus


class MessageCreate(BaseModel):
    sender: str = Field(min_length=1, max_length=80)
    recipient: str | None = Field(default=None, max_length=80)
    kind: MessageKind = "text"
    body: str = Field(min_length=1)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    thread_id: int
    sender: str
    recipient: str | None = None
    kind: str
    body: str
    created_at: datetime


class ThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    project_id: int | None = None
    created_by: str
    status: str
    created_at: datetime


class ThreadDetailOut(ThreadOut):
    messages: list[MessageOut] = []


class ThreadAdvanceOut(BaseModel):
    created: list[MessageOut] = []
