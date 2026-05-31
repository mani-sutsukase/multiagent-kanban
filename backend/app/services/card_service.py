from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.log import Log
from app.services.kanban_service import SwimlaneService


class CardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_card(self, kanban_id: str, title: str, content: str = "",
                          model: str = "claude-sonnet-4-20250514",
                          target_swimlane_id: str = None,
                          local_path: str = None,
                          local_path_permission: str = "read_write",
                          allowed_paths: str = "[]",
                          dangerously_skip_permissions: str = "0") -> Card:
        if not target_swimlane_id:
            swimlane_service = SwimlaneService(self.db)
            first = await swimlane_service.get_first_swimlane(kanban_id)
            if not first:
                raise ValueError("看板中没有泳道，无法创建卡片")
            target_swimlane_id = first.id

        card = Card(
            kanban_id=kanban_id,
            title=title,
            content=content,
            model=model,
            current_swimlane_id=target_swimlane_id,
            local_path=local_path,
            local_path_permission=local_path_permission,
            allowed_paths=allowed_paths,
            dangerously_skip_permissions=dangerously_skip_permissions,
            status="pending",
        )
        self.db.add(card)
        await self.db.commit()
        await self.db.refresh(card)
        return card

    async def get_card(self, card_id: str) -> Card | None:
        result = await self.db.execute(select(Card).where(Card.id == card_id))
        return result.scalar_one_or_none()

    async def update_card(self, card_id: str, **kwargs) -> Card | None:
        card = await self.get_card(card_id)
        if not card:
            return None
        for key, value in kwargs.items():
            setattr(card, key, value)
        await self.db.commit()
        await self.db.refresh(card)
        return card

    async def delete_card(self, card_id: str, terminate_callback=None) -> bool:
        card = await self.get_card(card_id)
        if not card:
            return False
        if card.status == "running" and terminate_callback:
            await terminate_callback(card_id)
        await self.db.delete(card)
        await self.db.commit()
        return True

    async def list_cards_by_kanban(self, kanban_id: str, swimlane_id: str = None,
                                   status: str = None) -> list[Card]:
        query = select(Card).where(Card.kanban_id == kanban_id)
        if swimlane_id:
            query = query.where(Card.current_swimlane_id == swimlane_id)
        if status:
            query = query.where(Card.status == status)
        query = query.order_by(Card.created_at)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_card_count_by_swimlane(self, kanban_id: str, swimlane_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Card.id)).where(
                Card.kanban_id == kanban_id,
                Card.current_swimlane_id == swimlane_id,
            )
        )
        return result.scalar() or 0

    async def clean_card(self, card_id: str) -> Card | None:
        """清理卡片的所有执行记录：清空执行数据、删除日志、重置到第一泳道"""
        card = await self.get_card(card_id)
        if not card:
            return None

        # 清空执行数据
        card.result = None
        card.last_prompt = None
        card.last_output = None
        card.session_id = None
        card.rejection_note = None
        card.user_reply = None
        card.user_reply_question = None

        # 删除所有日志
        await self.db.execute(delete(Log).where(Log.card_id == card_id))

        # 重置到第一泳道
        swimlane_service = SwimlaneService(self.db)
        first = await swimlane_service.get_first_swimlane(card.kanban_id)
        card.current_swimlane_id = first.id if first else None
        card.status = "pending"

        await self.db.commit()
        await self.db.refresh(card)
        return card
