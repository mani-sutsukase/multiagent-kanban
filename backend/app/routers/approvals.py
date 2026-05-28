from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import ws_manager
from app.services.approval_service import ApprovalService
from app.schemas.approval import ApprovalCreate, PendingApprovalResponse

router = APIRouter(prefix="/api")


@router.get("/approvals/pending", response_model=list[PendingApprovalResponse])
async def list_pending(db: AsyncSession = Depends(get_db)):
    service = ApprovalService(db)
    return await service.list_pending()


@router.post("/cards/{card_id}/approve")
async def approve_card(card_id: str, data: ApprovalCreate = None,
                       db: AsyncSession = Depends(get_db)):
    service = ApprovalService(db)
    card = await service.approve(card_id, data.note if data else None, ws_manager)
    if not card:
        raise HTTPException(status_code=400, detail="卡片不在待审批状态或不存在")
    return {"message": "已批准", "status": card.status}


@router.post("/cards/{card_id}/reject")
async def reject_card(card_id: str, data: ApprovalCreate,
                      db: AsyncSession = Depends(get_db)):
    if not data or not data.note or not data.note.strip():
        raise HTTPException(status_code=422, detail="驳回时必须提供批注")
    service = ApprovalService(db)
    card = await service.reject(card_id, data.note, ws_manager)
    if not card:
        raise HTTPException(status_code=400, detail="卡片不在待审批状态或不存在")
    return {"message": "已驳回", "status": card.status}
