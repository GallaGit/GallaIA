from pydantic import BaseModel, Field


class FsRootItem(BaseModel):
    root: str = Field(min_length=1, max_length=240)
    can_read: bool = True
    can_write: bool = False
    can_delete: bool = False


class AgentFsOut(BaseModel):
    agent_id: int | None = None
    agent_name: str
    roots: list[FsRootItem] = Field(default_factory=list)


class AgentFsUpdate(BaseModel):
    roots: list[FsRootItem] = Field(default_factory=list)
