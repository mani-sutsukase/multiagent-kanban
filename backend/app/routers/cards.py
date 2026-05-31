from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.card_service import CardService
from app.services.card_engine import CardEngine
from app.services.kanban_service import KanbanService
from app.services.agent_engine import agent_engine
from app.schemas.card import CardCreate, CardUpdate, CardResponse, ReplyRequest


class MoveCardRequest(BaseModel):
    target_swimlane_id: str

router = APIRouter(prefix="/api")


def _card_to_response(card) -> CardResponse:
    return CardResponse(
        id=card.id, kanban_id=card.kanban_id, title=card.title, content=card.content,
        model=card.model, current_swimlane_id=card.current_swimlane_id,
        status=card.status, session_id=card.session_id, rejection_note=card.rejection_note,
        result=card.result, last_prompt=card.last_prompt, last_output=card.last_output,
        user_reply=card.user_reply, user_reply_question=card.user_reply_question,
        local_path=card.local_path, local_path_permission=card.local_path_permission,
        allowed_paths=card.allowed_paths,
        dangerously_skip_permissions=card.dangerously_skip_permissions,
        created_at=card.created_at, updated_at=card.updated_at,
    )


@router.get("/kanbans/{kanban_id}/cards", response_model=list[CardResponse])
async def list_cards(kanban_id: str, swimlane_id: str = None, status: str = None,
                     db: AsyncSession = Depends(get_db)):
    service = CardService(db)
    kanban_service = KanbanService(db)
    if not await kanban_service.get(kanban_id):
        raise HTTPException(status_code=404, detail="看板不存在")
    cards = await service.list_cards_by_kanban(kanban_id, swimlane_id, status)
    return [_card_to_response(c) for c in cards]


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
            local_path=data.local_path,
            local_path_permission=data.local_path_permission,
            allowed_paths=data.allowed_paths,
            dangerously_skip_permissions="1" if data.dangerously_skip_permissions else "0",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _card_to_response(card)


@router.get("/cards/{card_id}", response_model=CardResponse)
async def get_card(card_id: str, db: AsyncSession = Depends(get_db)):
    service = CardService(db)
    card = await service.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return _card_to_response(card)


@router.put("/cards/{card_id}", response_model=CardResponse)
async def update_card(card_id: str, data: CardUpdate,
                      db: AsyncSession = Depends(get_db)):
    service = CardService(db)
    update_data = data.model_dump(exclude_none=True)
    # 手动将状态重置为 pending 时，清除之前的错误信息和驳回批注
    if update_data.get("status") == "pending":
        update_data["result"] = None
        update_data["rejection_note"] = None
    card = await service.update_card(card_id, **update_data)
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return _card_to_response(card)


@router.delete("/cards/{card_id}")
async def delete_card(card_id: str, db: AsyncSession = Depends(get_db)):
    service = CardService(db)
    success = await service.delete_card(card_id, agent_engine.terminate_card)
    if not success:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return {"message": "卡片已删除"}


@router.post("/cards/{card_id}/reply", response_model=CardResponse)
async def reply_to_card(card_id: str, data: ReplyRequest,
                        db: AsyncSession = Depends(get_db)):
    """用户回复 claude：保存回复后卡片重新进入 pending，由 picker 重新执行"""
    service = CardService(db)
    card = await service.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    if card.status != "waiting_for_reply":
        raise HTTPException(status_code=400, detail="卡片当前状态不允许回复，仅 waiting_for_reply 状态可回复")

    # 保存用户回复，将卡片重置为 pending
    card.user_reply = data.reply
    card.user_reply_question = None
    card.status = "pending"
    card.last_prompt = None  # 清除旧的提示词，下次执行时会重新生成
    card.last_output = None
    await db.commit()
    await db.refresh(card)

    # 懒导入避免循环依赖
    from app.main import ws_manager
    await ws_manager.broadcast({
        "type": "card_status_changed",
        "card_id": card.id,
        "status": "pending",
        "swimlane_id": card.current_swimlane_id,
    })

    return _card_to_response(card)


@router.post("/cards/{card_id}/advance", response_model=CardResponse)
async def advance_card(card_id: str, db: AsyncSession = Depends(get_db)):
    """用户在 waiting_for_reply 状态下手动推进到下一泳道"""
    service = CardService(db)
    card = await service.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    if card.status != "waiting_for_reply":
        raise HTTPException(status_code=400, detail="卡片当前状态不允许推进，仅 waiting_for_reply 状态可推进")

    card_engine = CardEngine(db)
    await card_engine.advance_to_next_swimlane(card)

    # 懒导入避免循环依赖
    from app.main import ws_manager
    await ws_manager.broadcast({
        "type": "card_status_changed",
        "card_id": card.id,
        "status": card.status,
        "swimlane_id": card.current_swimlane_id,
    })

    return _card_to_response(card)


@router.post("/cards/{card_id}/clean", response_model=CardResponse)
async def clean_card(card_id: str, db: AsyncSession = Depends(get_db)):
    """清理卡片的所有执行记录：清空执行数据、删除日志、重置到第一泳道"""
    service = CardService(db)
    card = await service.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")

    # 如果卡片正在运行，先终止
    if card.status == "running":
        await agent_engine.terminate_card(card_id)

    card = await service.clean_card(card_id)

    from app.main import ws_manager
    await ws_manager.broadcast({
        "type": "card_status_changed",
        "card_id": card.id,
        "status": card.status,
        "swimlane_id": card.current_swimlane_id,
    })

    return _card_to_response(card)


@router.post("/cards/{card_id}/move", response_model=CardResponse)
async def move_card(card_id: str, data: MoveCardRequest,
                    db: AsyncSession = Depends(get_db)):
    """拖拽移动卡片到目标泳道"""
    service = CardService(db)
    card = await service.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")

    # 如果卡片正在运行，先终止
    if card.status == "running":
        await agent_engine.terminate_card(card_id)

    card.current_swimlane_id = data.target_swimlane_id
    card.status = "pending"
    card.last_prompt = None
    card.last_output = None
    card.result = None
    card.user_reply_question = None
    await db.commit()
    await db.refresh(card)

    from app.main import ws_manager
    await ws_manager.broadcast({
        "type": "card_status_changed",
        "card_id": card.id,
        "status": card.status,
        "swimlane_id": card.current_swimlane_id,
    })

    return _card_to_response(card)


@router.post("/cards/{card_id}/terminate")
async def terminate_card(card_id: str, db: AsyncSession = Depends(get_db)):
    """终止正在运行的卡片，状态设为 blocked"""
    service = CardService(db)
    card = await service.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    if card.status != "running":
        raise HTTPException(status_code=400, detail="仅 running 状态的卡片可终止")

    # 先设置状态为 blocked（在进程退出回调之前），_on_process_exit 会检测到 blocked 不再覆盖
    card.status = "blocked"
    card.result = "用户手动终止执行"
    await db.commit()

    # 终止子进程
    await agent_engine.terminate_card(card_id)

    from app.main import ws_manager
    await ws_manager.broadcast({
        "type": "card_status_changed",
        "card_id": card_id,
        "status": "blocked",
        "swimlane_id": card.current_swimlane_id,
        "result": card.result,
    })

    return {"message": "卡片已终止", "status": "blocked"}
