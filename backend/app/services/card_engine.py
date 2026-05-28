from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.services.kanban_service import SwimlaneService, KanbanService
from app.services.card_service import CardService
from app.services.log_service import LogService


class CardEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.swimlane_service = SwimlaneService(db)
        self.card_service = CardService(db)
        self.log_service = LogService(db)

    async def is_last_swimlane(self, kanban_id: str, swimlane_id: str) -> bool:
        """判断是否是最后一个泳道"""
        swimlanes = await self.swimlane_service.get_kanban_swimlanes(kanban_id)
        if not swimlanes:
            return True
        return swimlanes[-1].id == swimlane_id

    async def advance_to_next_swimlane(self, card: Card) -> Card | None:
        """将卡片推进到下一个泳道"""
        swimlane = await self.swimlane_service.get(card.current_swimlane_id)
        if not swimlane:
            return None

        next_swimlane = await self.swimlane_service.get_next_swimlane(
            card.kanban_id, swimlane.sort_order
        )
        if not next_swimlane:
            # 最后一个泳道，标记为完成，但保留在最后一个泳道中展示
            card.status = "completed"
        else:
            # 进入下一个泳道
            card.current_swimlane_id = next_swimlane.id
            card.status = "pending"
            card.session_id = None
            card.rejection_note = None

        await self.db.commit()
        await self.db.refresh(card)
        return card

    async def handle_swimlane_completion(self, card: Card):
        """Agent 完成后根据 flow_mode 决策流转"""
        swimlane = await self.swimlane_service.get(card.current_swimlane_id)
        if not swimlane:
            return

        if swimlane.flow_mode == "auto":
            # 自动推进
            await self.advance_to_next_swimlane(card)
        elif swimlane.flow_mode == "pre_approval":
            # 等待审批
            card.status = "waiting_approval"
            await self.db.commit()
            await self.db.refresh(card)

    async def handle_approval(self, card: Card) -> Card | None:
        """批准后推进到下一泳道"""
        return await self.advance_to_next_swimlane(card)

    async def handle_rejection(self, card: Card, rejection_note: str) -> Card:
        """驳回后重置卡片状态为 running，保存 rejection_note"""
        card.status = "running"
        card.rejection_note = rejection_note
        await self.db.commit()
        await self.db.refresh(card)
        return card
