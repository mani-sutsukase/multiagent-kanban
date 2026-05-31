import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.approval import Approval
from app.models.kanban import Kanban, Swimlane
from app.models.log import Log
from app.services.card_engine import CardEngine


class ApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.card_engine = CardEngine(db)

    async def list_pending(self) -> list[dict]:
        """查询所有 waiting_approval 卡片，按看板分组"""
        result = await self.db.execute(
            select(Card, Kanban.name, Swimlane.name)
            .join(Kanban, Card.kanban_id == Kanban.id)
            .join(Swimlane, Card.current_swimlane_id == Swimlane.id)
            .where(Card.status == "waiting_approval")
            .order_by(Card.created_at)
        )
        rows = result.all()

        # 获取每个卡片的最新日志
        pending = []
        for card, kanban_name, swimlane_name in rows:
            log_result = await self.db.execute(
                select(Log).where(
                    Log.card_id == card.id,
                    Log.swimlane_id == card.current_swimlane_id,
                ).order_by(Log.attempt.desc()).limit(1)
            )
            latest_log = log_result.scalar_one_or_none()

            pending.append({
                "card_id": card.id,
                "card_title": card.title,
                "kanban_id": card.kanban_id,
                "kanban_name": kanban_name,
                "swimlane_id": card.current_swimlane_id,
                "swimlane_name": swimlane_name,
                "log_id": latest_log.id if latest_log else None,
                "created_at": card.created_at,
            })

        return pending

    async def approve(self, card_id: str, note: str = None, ws_manager=None) -> Card | None:
        """批准卡片，创建批准记录，触发推进或授权重新执行"""
        card = await self.db.execute(select(Card).where(Card.id == card_id))
        card = card.scalar_one_or_none()
        if not card or card.status != "waiting_approval":
            return None

        approval = Approval(
            id=str(uuid.uuid4()),
            card_id=card_id,
            swimlane_id=card.current_swimlane_id,
            action="approved",
            note=note,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.db.add(approval)

        # 泳道审批：推进到下一泳道
        new_card = await self.card_engine.handle_approval(card)

        if ws_manager:
            await ws_manager.broadcast({
                "type": "card_status_changed",
                "card_id": card_id,
                "status": new_card.status,
                "swimlane_id": new_card.current_swimlane_id,
                "result": new_card.result,
            })
            if new_card.status == "completed":
                await ws_manager.broadcast({
                    "type": "card_completed",
                    "card_id": card_id,
                    "swimlane_id": None,
                })

        return new_card

    async def reject(self, card_id: str, note: str, ws_manager=None) -> Card | None:
        """驳回卡片，保存批注，触发重执行"""
        if not note or not note.strip():
            raise ValueError("驳回时必须提供批注")

        card = await self.db.execute(select(Card).where(Card.id == card_id))
        card = card.scalar_one_or_none()
        if not card or card.status != "waiting_approval":
            return None

        approval = Approval(
            id=str(uuid.uuid4()),
            card_id=card_id,
            swimlane_id=card.current_swimlane_id,
            action="rejected",
            note=note,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.db.add(approval)

        # 泳道驳回：重新执行当前泳道（不推进）
        updated_card = await self.card_engine.handle_rejection(card, note)

        if ws_manager:
            await ws_manager.broadcast({
                "type": "card_status_changed",
                "card_id": card_id,
                "status": "pending",
                "swimlane_id": card.current_swimlane_id,
                "result": None,
            })

        return updated_card
