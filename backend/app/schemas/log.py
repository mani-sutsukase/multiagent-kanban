from pydantic import BaseModel
from typing import Optional


class LogResponse(BaseModel):
    id: str
    card_id: str
    swimlane_id: str
    attempt: int
    process_id: Optional[int] = None
    prompt: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    session_id: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class CardLogSummary(BaseModel):
    """已完成/异常卡片列表的摘要信息"""
    card_id: str
    card_title: str
    card_status: str
    kanban_id: str
    kanban_name: str
    log_id: Optional[str] = None
    swimlane_id: Optional[str] = None
    exit_code: Optional[int] = None
    session_id: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    stdout_preview: str = ""
