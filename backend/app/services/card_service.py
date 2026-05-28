from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.services.kanban_service import SwimlaneService


class CardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_card(self, kanban_id: str, title: str, content: str = "",
                          model: str = "claude-sonnet-4-20250514",
                          target_swimlane_id: str = None) -> Card:
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
            if value is not None:
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
