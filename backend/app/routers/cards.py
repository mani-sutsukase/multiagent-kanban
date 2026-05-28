from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.card_service import CardService
from app.services.kanban_service import KanbanService
from app.services.agent_engine import agent_engine
from app.schemas.card import CardCreate, CardUpdate, CardResponse

router = APIRouter(prefix="/api")


@router.get("/kanbans/{kanban_id}/cards", response_model=list[CardResponse])
async def list_cards(kanban_id: str, swimlane_id: str = None, status: str = None,
                     db: AsyncSession = Depends(get_db)):
    service = CardService(db)
    kanban_service = KanbanService(db)
    if not await kanban_service.get(kanban_id):
        raise HTTPException(status_code=404, detail="看板不存在")
    cards = await service.list_cards_by_kanban(kanban_id, swimlane_id, status)
    return [
        CardResponse(
            id=c.id, kanban_id=c.kanban_id, title=c.title, content=c.content,
            model=c.model, current_swimlane_id=c.current_swimlane_id,
            status=c.status, session_id=c.session_id, rejection_note=c.rejection_note,
            created_at=c.created_at, updated_at=c.updated_at,
        ) for c in cards
    ]


@router.post("/kanbans/{kanban_id}/cards", response_model=CardResponse, status_code=201)
async def create_card(kanban_id: str, data: CardCreate,
                      db: AsyncSession = Depends(get_db)):
    service = CardService(db)
    kanban_service = KanbanService(db)
    if not await kanban_service.get(kanban_id):
        raise HTTPException(status_code=404, detail="看板不存在")
    try:
        card = await service.create_card(
            kanban_id, data.title, data.content, data.model, data.target_swimlane_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return CardResponse(
        id=card.id, kanban_id=card.kanban_id, title=card.title, content=card.content,
        model=card.model, current_swimlane_id=card.current_swimlane_id,
        status=card.status, session_id=card.session_id, rejection_note=card.rejection_note,
        created_at=card.created_at, updated_at=card.updated_at,
    )


@router.get("/cards/{card_id}", response_model=CardResponse)
async def get_card(card_id: str, db: AsyncSession = Depends(get_db)):
    service = CardService(db)
    card = await service.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return CardResponse(
        id=card.id, kanban_id=card.kanban_id, title=card.title, content=card.content,
        model=card.model, current_swimlane_id=card.current_swimlane_id,
        status=card.status, session_id=card.session_id, rejection_note=card.rejection_note,
        created_at=card.created_at, updated_at=card.updated_at,
    )


@router.put("/cards/{card_id}", response_model=CardResponse)
async def update_card(card_id: str, data: CardUpdate,
                      db: AsyncSession = Depends(get_db)):
    service = CardService(db)
    card = await service.update_card(card_id, **data.model_dump(exclude_none=True))
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return CardResponse(
        id=card.id, kanban_id=card.kanban_id, title=card.title, content=card.content,
        model=card.model, current_swimlane_id=card.current_swimlane_id,
        status=card.status, session_id=card.session_id, rejection_note=card.rejection_note,
        created_at=card.created_at, updated_at=card.updated_at,
    )


@router.delete("/cards/{card_id}")
async def delete_card(card_id: str, db: AsyncSession = Depends(get_db)):
    service = CardService(db)
    success = await service.delete_card(card_id, agent_engine.terminate_card)
    if not success:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return {"message": "卡片已删除"}
