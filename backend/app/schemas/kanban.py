from pydantic import BaseModel
from typing import Optional


class KanbanCreate(BaseModel):
    name: str
    description: str = ""


class KanbanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class SwimlaneBrief(BaseModel):
    id: str
    name: str
    sort_order: int
    prompt: str = ""
    skill: Optional[str] = None
    tools: str = "[]"
    flow_mode: str
    local_path: Optional[str] = None
    card_count: int = 0

    class Config:
        from_attributes = True


class KanbanResponse(BaseModel):
    id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    swimlanes: list[SwimlaneBrief] = []

    class Config:
        from_attributes = True


class SwimlaneCreate(BaseModel):
    name: str
    prompt: str = ""
    skill: Optional[str] = None
    tools: str = "[]"
    flow_mode: str = "auto"
    local_path: Optional[str] = None


class SwimlaneUpdate(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None
    skill: Optional[str] = None
    tools: Optional[str] = None
    flow_mode: Optional[str] = None
    local_path: Optional[str] = None


class SwimlaneResponse(BaseModel):
    id: str
    kanban_id: str
    name: str
    sort_order: int
    prompt: str
    skill: Optional[str] = None
    tools: str
    flow_mode: str
    local_path: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SwimlaneOrderRequest(BaseModel):
    swimlane_ids: list[str]
