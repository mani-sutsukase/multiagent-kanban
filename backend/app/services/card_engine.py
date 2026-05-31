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
            # 最后一个泳道，标记为完成
            card.status = "completed"
            card.result = "任务执行成功：任务已完成"
        else:
            # 进入下一个泳道，清除当前泳道的执行结果
            card.current_swimlane_id = next_swimlane.id
            card.status = "pending"
            card.session_id = None
            card.rejection_note = None
            card.result = None
            card.user_reply_question = None

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

    async def handle_authorize_approval(self, card: Card) -> Card:
        """用户批准授权请求后，重新执行（不推进泳道）

        保留 session_id 以便 _build_claude_args 使用 --resume 恢复 Claude 会话，
        这样 Claude 能记住之前的对话上下文和文件操作状态。
        """
        card.user_reply = "已授权，请继续执行"
        card.rejection_note = None
        card.status = "pending"
        # 注意：不清空 session_id，让 Claude 以 --resume 恢复会话
        await self.db.commit()
        await self.db.refresh(card)
        return card

    async def handle_authorize_rejection(self, card: Card, rejection_note: str) -> Card:
        """用户驳回授权请求后，重新执行（不推进泳道）"""
        card.rejection_note = rejection_note
        card.user_reply = None
        card.status = "pending"
        card.session_id = None
        await self.db.commit()
        await self.db.refresh(card)
        return card

    async def handle_rejection(self, card: Card, rejection_note: str) -> Card:
        """驳回后重置卡片状态为 pending（重新入队），保存 rejection_note，清除旧执行结果"""
        card.status = "pending"
        card.rejection_note = rejection_note
        card.result = None
        await self.db.commit()
        await self.db.refresh(card)
        return card
