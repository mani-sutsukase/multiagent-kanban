from pydantic import BaseModel
from typing import Optional


class CardCreate(BaseModel):
    title: str
    content: str = ""
    model: str = "claude-sonnet-4-20250514"
    target_swimlane_id: Optional[str] = None
    local_path: Optional[str] = None
    local_path_permission: str = "read_write"
    allowed_paths: str = "[]"
    dangerously_skip_permissions: bool = False


class CardUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    model: Optional[str] = None
    status: Optional[str] = None
    local_path: Optional[str] = None
    local_path_permission: Optional[str] = None
    allowed_paths: Optional[str] = None
    dangerously_skip_permissions: Optional[bool] = None


class CardResponse(BaseModel):
    id: str
    kanban_id: str
    title: str
    content: str
    model: str
    current_swimlane_id: Optional[str] = None
    status: str
    session_id: Optional[str] = None
    rejection_note: Optional[str] = None
    result: Optional[str] = None
    last_prompt: Optional[str] = None
    last_output: Optional[str] = None
    user_reply: Optional[str] = None
    user_reply_question: Optional[str] = None
    local_path: Optional[str] = None
    local_path_permission: str = "read_write"
    allowed_paths: str = "[]"
    dangerously_skip_permissions: str = "0"
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CardStatusResponse(BaseModel):
    id: str
    status: str
    current_swimlane_id: Optional[str] = None
    session_id: Optional[str] = None
    result: Optional[str] = None


class ReplyRequest(BaseModel):
    reply: str
