from pydantic import BaseModel
from typing import Optional


class ScheduleCreate(BaseModel):
    name: str
    description: str = ""
    cron_expr: str
    card_title: str
    card_content: str = ""
    card_model: str = "claude-sonnet-4-20250514"
    target_kanban_id: str
    target_swimlane_id: str


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cron_expr: Optional[str] = None
    card_title: Optional[str] = None
    card_content: Optional[str] = None
    card_model: Optional[str] = None
    target_kanban_id: Optional[str] = None
    target_swimlane_id: Optional[str] = None


class ScheduleResponse(BaseModel):
    id: str
    name: str
    description: str
    cron_expr: str
    enabled: int
    card_title: str
    card_content: str
    card_model: str
    target_kanban_id: str
    target_swimlane_id: str
    next_run_time: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ScheduleLogResponse(BaseModel):
    id: str
    schedule_id: str
    triggered_at: str
    created_card_id: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True
