from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kanban import Kanban, Swimlane
from app.models.card import Card


class KanbanService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, name: str, description: str = "") -> Kanban:
        kanban = Kanban(name=name, description=description)
        self.db.add(kanban)
        await self.db.commit()
        await self.db.refresh(kanban)
        return kanban

    async def get(self, kanban_id: str) -> Kanban | None:
        result = await self.db.execute(select(Kanban).where(Kanban.id == kanban_id))
        return result.scalar_one_or_none()

    async def list(self) -> list[Kanban]:
        result = await self.db.execute(select(Kanban).order_by(Kanban.created_at))
        return list(result.scalars().all())

    async def update(self, kanban_id: str, **kwargs) -> Kanban | None:
        kanban = await self.get(kanban_id)
        if not kanban:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(kanban, key, value)
        await self.db.commit()
        await self.db.refresh(kanban)
        return kanban

    async def delete(self, kanban_id: str) -> bool:
        kanban = await self.get(kanban_id)
        if not kanban:
            return False
        await self.db.delete(kanban)
        await self.db.commit()
        return True

    async def get_swimlane_count(self, kanban_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Swimlane.id)).where(Swimlane.kanban_id == kanban_id)
        )
        return result.scalar() or 0

    async def get_card_count(self, kanban_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Card.id)).where(Card.kanban_id == kanban_id)
        )
        return result.scalar() or 0

    async def export_config(self, kanban_id: str) -> dict | None:
        """导出看板配置（仅结构，不含卡片等执行数据）"""
        kanban = await self.get(kanban_id)
        if not kanban:
            return None
        from datetime import datetime, timezone
        swimlane_service = SwimlaneService(self.db)
        swimlanes = await swimlane_service.get_kanban_swimlanes(kanban_id)
        return {
            "version": 1,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "kanban": {
                "name": kanban.name,
                "description": kanban.description or "",
            },
            "swimlanes": [
                {
                    "name": s.name,
                    "sort_order": s.sort_order,
                    "prompt": s.prompt or "",
                    "skill": s.skill,
                    "tools": s.tools or "[]",
                    "swimlane_type": s.swimlane_type or "normal",
                    "flow_mode": s.flow_mode,
                    "local_path": s.local_path,
                    "wait_for_reply": s.wait_for_reply or "1",
                    "local_path_permission": s.local_path_permission or "read_write",
                    "allowed_paths": s.allowed_paths or "[]",
                }
                for s in swimlanes
            ],
        }

    async def import_config(self, data: dict):
        """从配置字典导入看板，返回创建的 Kanban ORM 对象"""
        version = data.get("version", 1)
        if version != 1:
            raise ValueError(f"不支持的导出版本: {version}")

        kanban_data = data["kanban"]
        kanban = await self.create(
            name=kanban_data["name"],
            description=kanban_data.get("description", ""),
        )

        swimlane_service = SwimlaneService(self.db)
        for sl_data in data.get("swimlanes", []):
            await swimlane_service.add_swimlane(
                kanban_id=kanban.id,
                name=sl_data["name"],
                prompt=sl_data.get("prompt", ""),
                skill=sl_data.get("skill"),
                tools=sl_data.get("tools", "[]"),
                swimlane_type=sl_data.get("swimlane_type", "normal"),
                flow_mode=sl_data.get("flow_mode", "auto"),
                local_path=sl_data.get("local_path"),
                wait_for_reply=sl_data.get("wait_for_reply", "1"),
                local_path_permission=sl_data.get("local_path_permission", "read_write"),
                allowed_paths=sl_data.get("allowed_paths", "[]"),
            )

        await self.db.refresh(kanban)
        return kanban


class SwimlaneService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_swimlane(self, kanban_id: str, name: str, prompt: str = "",
                           skill: str = None, tools: str = "[]",
                           swimlane_type: str = "normal",
                           flow_mode: str = "auto",
                           local_path: str = None,
                           wait_for_reply: str = "0",
                           local_path_permission: str = "read_write",
                           allowed_paths: str = "[]") -> Swimlane:
        # 获取当前最大 sort_order
        result = await self.db.execute(
            select(func.max(Swimlane.sort_order)).where(Swimlane.kanban_id == kanban_id)
        )
        max_order = result.scalar() or -1

        swimlane = Swimlane(
            kanban_id=kanban_id,
            name=name,
            sort_order=max_order + 1,
            prompt=prompt,
            skill=skill,
            tools=tools,
            swimlane_type=swimlane_type,
            flow_mode=flow_mode,
            local_path=local_path,
            local_path_permission=local_path_permission,
            allowed_paths=allowed_paths,
            wait_for_reply=wait_for_reply,
        )
        self.db.add(swimlane)
        await self.db.commit()
        await self.db.refresh(swimlane)
        return swimlane

    async def get(self, swimlane_id: str) -> Swimlane | None:
        result = await self.db.execute(select(Swimlane).where(Swimlane.id == swimlane_id))
        return result.scalar_one_or_none()

    async def update(self, swimlane_id: str, **kwargs) -> Swimlane | None:
        swimlane = await self.get(swimlane_id)
        if not swimlane:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(swimlane, key, value)
        await self.db.commit()
        await self.db.refresh(swimlane)
        return swimlane

    async def delete(self, swimlane_id: str) -> tuple[bool, str]:
        """Delete swimlane. Returns (success, error_message)."""
        swimlane = await self.get(swimlane_id)
        if not swimlane:
            return False, "泳道不存在"

        # 检查是否有运行中的卡片
        result = await self.db.execute(
            select(func.count(Card.id)).where(
                Card.current_swimlane_id == swimlane_id,
                Card.status == "running",
            )
        )
        running_count = result.scalar() or 0
        if running_count > 0:
            return False, f"该泳道有 {running_count} 张运行中的卡片，无法删除"

        await self.db.delete(swimlane)
        await self.db.commit()
        return True, ""

    async def reorder(self, kanban_id: str, swimlane_ids: list[str]) -> bool:
        for i, sid in enumerate(swimlane_ids):
            await self.db.execute(
                __import__("sqlalchemy").update(Swimlane)
                .where(Swimlane.id == sid, Swimlane.kanban_id == kanban_id)
                .values(sort_order=i)
            )
        await self.db.commit()
        return True

    async def get_kanban_swimlanes(self, kanban_id: str) -> list[Swimlane]:
        result = await self.db.execute(
            select(Swimlane).where(Swimlane.kanban_id == kanban_id)
            .order_by(Swimlane.sort_order)
        )
        return list(result.scalars().all())

    async def get_first_swimlane(self, kanban_id: str) -> Swimlane | None:
        result = await self.db.execute(
            select(Swimlane).where(Swimlane.kanban_id == kanban_id)
            .order_by(Swimlane.sort_order).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_next_swimlane(self, kanban_id: str, current_sort_order: int) -> Swimlane | None:
        result = await self.db.execute(
            select(Swimlane).where(
                Swimlane.kanban_id == kanban_id,
                Swimlane.sort_order > current_sort_order,
            ).order_by(Swimlane.sort_order).limit(1)
        )
        return result.scalar_one_or_none()
