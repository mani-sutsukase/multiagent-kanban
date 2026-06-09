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
    swimlane_type: str = "normal"
    flow_mode: str
    local_path: Optional[str] = None
    wait_for_reply: str = "1"
    local_path_permission: str = "read_write"
    allowed_paths: str = "[]"
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
    swimlane_type: str = "normal"
    flow_mode: str = "auto"
    local_path: Optional[str] = None
    wait_for_reply: str = "1"
    local_path_permission: str = "read_write"
    allowed_paths: str = "[]"


class SwimlaneUpdate(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None
    skill: Optional[str] = None
    tools: Optional[str] = None
    swimlane_type: Optional[str] = None
    flow_mode: Optional[str] = None
    local_path: Optional[str] = None
    wait_for_reply: Optional[str] = None
    local_path_permission: Optional[str] = None
    allowed_paths: Optional[str] = None


class SwimlaneResponse(BaseModel):
    id: str
    kanban_id: str
    name: str
    sort_order: int
    prompt: str
    skill: Optional[str] = None
    tools: str
    swimlane_type: str
    flow_mode: str
    local_path: Optional[str] = None
    wait_for_reply: str = "1"
    local_path_permission: str = "read_write"
    allowed_paths: str = "[]"
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SwimlaneOrderRequest(BaseModel):
    swimlane_ids: list[str]


# === 导出/导入 Schema ===

class KanbanExportSwimlane(BaseModel):
    """导出用泳道结构 — 不含 id/kanban_id/created_at/updated_at"""
    name: str
    sort_order: int = 0
    prompt: str = ""
    skill: Optional[str] = None
    tools: str = "[]"
    swimlane_type: str = "normal"
    flow_mode: str = "auto"
    local_path: Optional[str] = None
    wait_for_reply: str = "1"
    local_path_permission: str = "read_write"
    allowed_paths: str = "[]"


class KanbanImportData(BaseModel):
    """导入请求"""
    version: int = 1
    kanban: KanbanCreate
    swimlanes: list[KanbanExportSwimlane] = []


class KanbanImportResult(BaseModel):
    """导入结果"""
    id: str
    name: str
    description: str
    swimlane_count: int
    message: str = "看板导入成功"
