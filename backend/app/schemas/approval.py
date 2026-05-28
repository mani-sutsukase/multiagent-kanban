from pydantic import BaseModel
from typing import Optional


class ApprovalCreate(BaseModel):
    note: Optional[str] = None


class ApprovalResponse(BaseModel):
    id: str
    card_id: str
    swimlane_id: str
    action: str
    note: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class PendingApprovalResponse(BaseModel):
    card_id: str
    card_title: str
    kanban_id: str
    kanban_name: str
    swimlane_id: str
    swimlane_name: str
    log_id: Optional[str] = None
    created_at: str
