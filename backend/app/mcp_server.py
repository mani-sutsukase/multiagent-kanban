"""MCP Server — 将 MultiAgent Kanban 所有系统操作暴露为 MCP Tools

供编排泳道中的 Claude CLI（通过 --mcp-servers）和外部 Claude Desktop 客户端调用。
所有工具直接复用 Service 层，不走 HTTP REST。
"""

import json
from datetime import datetime, timezone

from app.database import async_session_factory
from app.services.kanban_service import KanbanService, SwimlaneService
from app.services.card_service import CardService
from app.services.approval_service import ApprovalService
from app.services.card_engine import CardEngine
from app.services.log_service import LogService
from app.models.card import Card


def _now():
    return datetime.now(timezone.utc).isoformat()


def create_mcp_server():
    """创建 MCP Server 实例并注册所有工具"""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        raise ImportError("请安装 mcp 包: pip install mcp>=1.0.0")

    mcp = FastMCP("MultiAgent Kanban")

    # ========================================================================
    # Kanban 管理
    # ========================================================================

    @mcp.tool(description="列出所有看板（含泳道摘要）")
    async def list_kanbans() -> str:
        """列出所有看板，返回 JSON 数组"""
        async with async_session_factory() as db:
            svc = KanbanService(db)
            sw_svc = SwimlaneService(db)
            kanbans = await svc.list()
            result = []
            for k in kanbans:
                swimlanes = await sw_svc.get_kanban_swimlanes(k.id)
                result.append({
                    "id": k.id,
                    "name": k.name,
                    "description": k.description or "",
                    "swimlane_count": len(swimlanes),
                    "swimlanes": [{"id": s.id, "name": s.name, "sort_order": s.sort_order,
                                   "flow_mode": s.flow_mode, "swimlane_type": s.swimlane_type}
                                  for s in swimlanes],
                    "created_at": k.created_at,
                })
            return json.dumps(result, ensure_ascii=False)

    @mcp.tool(description="获取单个看板详情（含完整泳道信息）")
    async def get_kanban(kanban_id: str) -> str:
        """获取看板详情"""
        async with async_session_factory() as db:
            svc = KanbanService(db)
            sw_svc = SwimlaneService(db)
            kanban = await svc.get(kanban_id)
            if not kanban:
                return json.dumps({"error": "看板不存在"})
            swimlanes = await sw_svc.get_kanban_swimlanes(kanban_id)
            return json.dumps({
                "id": kanban.id,
                "name": kanban.name,
                "description": kanban.description or "",
                "swimlanes": [{"id": s.id, "name": s.name, "sort_order": s.sort_order,
                               "prompt": s.prompt or "", "skill": s.skill,
                               "flow_mode": s.flow_mode, "swimlane_type": s.swimlane_type}
                              for s in swimlanes],
                "created_at": kanban.created_at,
                "updated_at": kanban.updated_at,
            }, ensure_ascii=False)

    @mcp.tool(description="创建新看板")
    async def create_kanban(name: str, description: str = "") -> str:
        """创建看板，返回看板信息"""
        async with async_session_factory() as db:
            svc = KanbanService(db)
            kanban = await svc.create(name.strip(), description)
            return json.dumps({
                "id": kanban.id,
                "name": kanban.name,
                "description": kanban.description or "",
                "message": "看板创建成功",
            }, ensure_ascii=False)

    @mcp.tool(description="更新看板名称或描述")
    async def update_kanban(kanban_id: str, name: str = None, description: str = None) -> str:
        """更新看板信息"""
        async with async_session_factory() as db:
            svc = KanbanService(db)
            kwargs = {}
            if name is not None:
                kwargs["name"] = name.strip()
            if description is not None:
                kwargs["description"] = description
            kanban = await svc.update(kanban_id, **kwargs)
            if not kanban:
                return json.dumps({"error": "看板不存在"})
            return json.dumps({"id": kanban.id, "name": kanban.name, "message": "看板已更新"}, ensure_ascii=False)

    @mcp.tool(description="删除看板（会级联删除所有泳道和卡片）")
    async def delete_kanban(kanban_id: str) -> str:
        """删除看板"""
        async with async_session_factory() as db:
            svc = KanbanService(db)
            success = await svc.delete(kanban_id)
            if not success:
                return json.dumps({"error": "看板不存在"})
            return json.dumps({"message": "看板已删除"}, ensure_ascii=False)

    # ========================================================================
    # Swimlane 管理
    # ========================================================================

    @mcp.tool(description="向看板添加泳道")
    async def add_swimlane(
        kanban_id: str,
        name: str,
        prompt: str = "",
        skill: str = None,
        flow_mode: str = "auto",
        swimlane_type: str = "normal",
        local_path: str = None,
        wait_for_reply: str = "1",
        local_path_permission: str = "read_write",
        allowed_paths: str = "[]",
    ) -> str:
        """向看板添加一个新泳道"""
        async with async_session_factory() as db:
            svc = SwimlaneService(db)
            s = await svc.add_swimlane(
                kanban_id, name, prompt, skill, "[]",
                swimlane_type, flow_mode,
                local_path, wait_for_reply, local_path_permission, allowed_paths,
            )
            return json.dumps({
                "id": s.id,
                "name": s.name,
                "sort_order": s.sort_order,
                "swimlane_type": s.swimlane_type,
                "flow_mode": s.flow_mode,
                "message": "泳道创建成功",
            }, ensure_ascii=False)

    @mcp.tool(description="更新泳道配置")
    async def update_swimlane(
        swimlane_id: str,
        name: str = None,
        prompt: str = None,
        skill: str = None,
        flow_mode: str = None,
        swimlane_type: str = None,
        local_path: str = None,
        wait_for_reply: str = None,
        local_path_permission: str = None,
        allowed_paths: str = None,
    ) -> str:
        """更新泳道的属性"""
        async with async_session_factory() as db:
            svc = SwimlaneService(db)
            kwargs = {k: v for k, v in locals().items()
                      if k not in ("db", "svc", "swimlane_id") and v is not None}
            kwargs.pop("swimlane_id", None)
            s = await svc.update(swimlane_id, **kwargs)
            if not s:
                return json.dumps({"error": "泳道不存在"})
            return json.dumps({"id": s.id, "name": s.name, "message": "泳道已更新"}, ensure_ascii=False)

    @mcp.tool(description="删除泳道（如有运行中的卡片则无法删除）")
    async def delete_swimlane(swimlane_id: str) -> str:
        """删除泳道"""
        async with async_session_factory() as db:
            svc = SwimlaneService(db)
            success, msg = await svc.delete(swimlane_id)
            if not success:
                return json.dumps({"error": msg})
            return json.dumps({"message": "泳道已删除"}, ensure_ascii=False)

    @mcp.tool(description="重新排序看板的泳道")
    async def reorder_swimlanes(kanban_id: str, swimlane_ids: list) -> str:
        """按 swimlane_ids 的顺序重新排列泳道"""
        async with async_session_factory() as db:
            svc = SwimlaneService(db)
            await svc.reorder(kanban_id, swimlane_ids)
            return json.dumps({"message": "泳道顺序已更新"}, ensure_ascii=False)

    # ========================================================================
    # Card 管理
    # ========================================================================

    @mcp.tool(description="列出看板下的卡片（可按泳道和状态过滤）")
    async def list_cards(kanban_id: str = None, swimlane_id: str = None, status: str = None) -> str:
        """列出卡片，支持过滤"""
        if not kanban_id:
            return json.dumps({"error": "kanban_id 是必填参数"})
        async with async_session_factory() as db:
            svc = CardService(db)
            cards = await svc.list_cards_by_kanban(kanban_id, swimlane_id=swimlane_id, status=status)
            result = []
            for c in cards:
                result.append({
                    "id": c.id,
                    "title": c.title,
                    "content": c.content or "",
                    "status": c.status,
                    "current_swimlane_id": c.current_swimlane_id,
                    "result": c.result or "",
                    "created_at": c.created_at,
                })
            return json.dumps(result, ensure_ascii=False)

    @mcp.tool(description="获取单张卡片的详细信息（含当前泳道和日志）")
    async def get_card(card_id: str) -> str:
        """获取卡片详情"""
        async with async_session_factory() as db:
            svc = CardService(db)
            card = await svc.get_card(card_id)
            if not card:
                return json.dumps({"error": "卡片不存在"})
            return json.dumps({
                "id": card.id,
                "kanban_id": card.kanban_id,
                "title": card.title,
                "content": card.content or "",
                "status": card.status,
                "current_swimlane_id": card.current_swimlane_id,
                "model": card.model,
                "result": card.result or "",
                "last_output": card.last_output or "",
                "rejection_note": card.rejection_note or "",
                "user_reply_question": card.user_reply_question or "",
                "created_at": card.created_at,
            }, ensure_ascii=False)

    @mcp.tool(description="在看板中创建新卡片")
    async def create_card(kanban_id: str, title: str, content: str = "",
                          target_swimlane_id: str = None, model: str = None) -> str:
        """创建卡片（状态为 pending，自动进入目标泳道或第一泳道）"""
        async with async_session_factory() as db:
            svc = CardService(db)
            card = await svc.create_card(
                kanban_id=kanban_id, title=title.strip(),
                content=content, target_swimlane_id=target_swimlane_id,
                model=model,
            )
            return json.dumps({
                "id": card.id,
                "title": card.title,
                "status": card.status,
                "current_swimlane_id": card.current_swimlane_id,
                "message": "卡片创建成功",
            }, ensure_ascii=False)

    @mcp.tool(description="更新卡片属性（设为 pending 会清除执行结果）")
    async def update_card(card_id: str, title: str = None, content: str = None,
                          status: str = None, model: str = None) -> str:
        """更新卡片"""
        async with async_session_factory() as db:
            svc = CardService(db)
            kwargs = {k: v for k, v in locals().items()
                      if k not in ("db", "svc", "card_id") and v is not None}
            kwargs.pop("card_id", None)
            card = await svc.update_card(card_id, **kwargs)
            if not card:
                return json.dumps({"error": "卡片不存在"})
            return json.dumps({"id": card.id, "title": card.title, "status": card.status,
                               "message": "卡片已更新"}, ensure_ascii=False)

    @mcp.tool(description="删除卡片（如正在运行则先终止）")
    async def delete_card(card_id: str) -> str:
        """删除卡片"""
        from app.services.agent_engine import agent_engine
        async with async_session_factory() as db:
            svc = CardService(db)
            success = await svc.delete_card(card_id, terminate_callback=agent_engine.terminate_card)
            if not success:
                return json.dumps({"error": "卡片不存在"})
            return json.dumps({"message": "卡片已删除"}, ensure_ascii=False)

    @mcp.tool(description="将卡片移动到指定的目标泳道")
    async def move_card(card_id: str, target_swimlane_id: str) -> str:
        """移动卡片到其他泳道"""
        async with async_session_factory() as db:
            card = await db.get(Card, card_id)
            if not card:
                return json.dumps({"error": "卡片不存在"})
            card.current_swimlane_id = target_swimlane_id
            card.status = "pending"
            await db.commit()
            return json.dumps({"message": "卡片已移动", "card_id": card_id,
                               "target_swimlane_id": target_swimlane_id}, ensure_ascii=False)

    @mcp.tool(description="获取卡片的执行日志列表")
    async def get_card_logs(card_id: str) -> str:
        """获取卡片的所有执行日志"""
        async with async_session_factory() as db:
            svc = LogService(db)
            logs = await svc.get_card_logs(card_id)
            result = []
            for log in logs:
                result.append({
                    "id": log.id,
                    "swimlane_id": log.swimlane_id,
                    "attempt": log.attempt,
                    "exit_code": log.exit_code,
                    "started_at": log.started_at or "",
                    "finished_at": log.finished_at or "",
                    "stdout_preview": (log.stdout or "")[:500] if log.stdout else "",
                    "stderr_preview": (log.stderr or "")[:500] if log.stderr else "",
                })
            return json.dumps(result, ensure_ascii=False)

    # ========================================================================
    # 审批 & 回复
    # ========================================================================

    @mcp.tool(description="列出所有待审批的卡片")
    async def list_pending_approvals() -> str:
        """列出 waiting_approval 状态的卡片详情"""
        async with async_session_factory() as db:
            svc = ApprovalService(db)
            items = await svc.list_pending()
            result = []
            for item in items:
                result.append({
                    "card_id": item.card_id,
                    "card_title": item.card_title,
                    "kanban_name": item.kanban_name,
                    "swimlane_name": item.swimlane_name,
                    "log_id": item.log_id,
                })
            return json.dumps(result, ensure_ascii=False)

    @mcp.tool(description="审批通过一张等待审批的卡片")
    async def approve_card(card_id: str, note: str = "") -> str:
        """审批通过，卡片推进到下一泳道"""
        async with async_session_factory() as db:
            svc = ApprovalService(db)
            result = await svc.approve(card_id, note, ws_manager=None)
            if not result:
                return json.dumps({"error": "卡片不存在或状态不是 waiting_approval"})
            return json.dumps({"message": f"卡片 {card_id} 已审批通过", "card_id": card_id}, ensure_ascii=False)

    @mcp.tool(description="驳回一张等待审批的卡片")
    async def reject_card(card_id: str, note: str = "") -> str:
        """审批驳回，卡片回到当前泳道重试"""
        async with async_session_factory() as db:
            svc = ApprovalService(db)
            if not note or not note.strip():
                return json.dumps({"error": "驳回时必须提供批注"})
            result = await svc.reject(card_id, note, ws_manager=None)
            if not result:
                return json.dumps({"error": "卡片不存在或状态不是 waiting_approval"})
            return json.dumps({"message": f"卡片 {card_id} 已驳回", "card_id": card_id}, ensure_ascii=False)

    @mcp.tool(description="回复一张等待用户回复的卡片")
    async def reply_to_card(card_id: str, reply: str) -> str:
        """回复 Claude 的提问，卡片继续执行"""
        async with async_session_factory() as db:
            card = await db.get(Card, card_id)
            if not card:
                return json.dumps({"error": "卡片不存在"})
            if card.status != "waiting_for_reply":
                return json.dumps({"error": f"卡片状态为 {card.status}，不在等待回复状态"})
            card.user_reply = reply
            card.last_prompt = None
            card.last_output = None
            card.status = "pending"
            await db.commit()
            return json.dumps({"message": f"已回复卡片 {card_id}，卡片将继续执行",
                               "card_id": card_id}, ensure_ascii=False)

    # ========================================================================
    # 定时任务
    # ========================================================================

    @mcp.tool(description="列出所有定时任务")
    async def list_schedules() -> str:
        """列出所有定时任务"""
        async with async_session_factory() as db:
            from app.models.schedule import Schedule
            from sqlalchemy import select
            result = await db.execute(select(Schedule))
            schedules = result.scalars().all()
            data = []
            for s in schedules:
                data.append({
                    "id": s.id,
                    "cron_expr": s.cron_expr,
                    "card_title": s.card_title,
                    "target_kanban_id": s.target_kanban_id,
                    "target_swimlane_id": s.target_swimlane_id,
                    "enabled": bool(s.enabled),
                    "created_at": s.created_at,
                })
            return json.dumps(data, ensure_ascii=False)

    @mcp.tool(description="创建定时任务（cron 表达式触发创建卡片）")
    async def create_schedule(
        cron_expr: str,
        card_title: str,
        target_kanban_id: str,
        target_swimlane_id: str = None,
        card_content: str = "",
        card_model: str = None,
        enabled: bool = True,
    ) -> str:
        """创建定时任务"""
        from sqlalchemy import select
        async with async_session_factory() as db:
            from app.models.schedule import Schedule
            schedule = Schedule(
                cron_expr=cron_expr,
                card_title=card_title,
                card_content=card_content,
                card_model=card_model,
                target_kanban_id=target_kanban_id,
                target_swimlane_id=target_swimlane_id,
                enabled=1 if enabled else 0,
            )
            db.add(schedule)
            await db.commit()
            await db.refresh(schedule)

        # 注册到调度引擎
        from app.services.schedule_engine import schedule_engine
        await schedule_engine.add_schedule_job(schedule.id, cron_expr,
                                                 target_kanban_id, target_swimlane_id,
                                                 card_title, card_content, card_model)

        return json.dumps({
            "id": schedule.id,
            "cron_expr": cron_expr,
            "card_title": card_title,
            "message": "定时任务创建成功",
        }, ensure_ascii=False)

    @mcp.tool(description="更新定时任务配置")
    async def update_schedule(schedule_id: str, cron_expr: str = None,
                               card_title: str = None, enabled: bool = None) -> str:
        """更新定时任务"""
        from sqlalchemy import select
        async with async_session_factory() as db:
            from app.models.schedule import Schedule
            schedule = await db.get(Schedule, schedule_id)
            if not schedule:
                return json.dumps({"error": "定时任务不存在"})
            if cron_expr is not None:
                schedule.cron_expr = cron_expr
            if card_title is not None:
                schedule.card_title = card_title
            if enabled is not None:
                schedule.enabled = 1 if enabled else 0
            await db.commit()

        # 更新调度器
        from app.services.schedule_engine import schedule_engine
        await schedule_engine.remove_schedule_job(schedule_id)
        if enabled if enabled is not None else bool(schedule.enabled):
            await schedule_engine.add_schedule_job(
                schedule.id, schedule.cron_expr,
                schedule.target_kanban_id, schedule.target_swimlane_id,
                schedule.card_title, schedule.card_content, schedule.card_model,
            )

        return json.dumps({"message": "定时任务已更新", "id": schedule_id}, ensure_ascii=False)

    @mcp.tool(description="删除定时任务")
    async def delete_schedule(schedule_id: str) -> str:
        """删除定时任务"""
        from sqlalchemy import select
        async with async_session_factory() as db:
            from app.models.schedule import Schedule
            schedule = await db.get(Schedule, schedule_id)
            if not schedule:
                return json.dumps({"error": "定时任务不存在"})
            await db.delete(schedule)
            await db.commit()

        from app.services.schedule_engine import schedule_engine
        await schedule_engine.remove_schedule_job(schedule_id)
        return json.dumps({"message": "定时任务已删除"}, ensure_ascii=False)

    @mcp.tool(description="启用或禁用一个定时任务")
    async def toggle_schedule(schedule_id: str) -> str:
        """切换定时任务的启用/禁用状态"""
        from sqlalchemy import select
        async with async_session_factory() as db:
            from app.models.schedule import Schedule
            schedule = await db.get(Schedule, schedule_id)
            if not schedule:
                return json.dumps({"error": "定时任务不存在"})
            schedule.enabled = 0 if schedule.enabled else 1
            await db.commit()
            enabled = bool(schedule.enabled)

        from app.services.schedule_engine import schedule_engine
        if enabled:
            await schedule_engine.remove_schedule_job(schedule_id)
        else:
            await schedule_engine.add_schedule_job(
                schedule.id, schedule.cron_expr,
                schedule.target_kanban_id, schedule.target_swimlane_id,
                schedule.card_title, schedule.card_content, schedule.card_model,
            )

        return json.dumps({"message": f"定时任务已{'启用' if enabled else '禁用'}",
                           "enabled": enabled}, ensure_ascii=False)

    # ========================================================================
    # 设置 & 系统
    # ========================================================================

    @mcp.tool(description="列出所有系统设置")
    async def list_settings() -> str:
        """列出所有配置项"""
        async with async_session_factory() as db:
            from app.models.setting import Setting
            from sqlalchemy import select
            result = await db.execute(select(Setting))
            settings = result.scalars().all()
            data = {s.key: s.value for s in settings}
            return json.dumps(data, ensure_ascii=False)

    @mcp.tool(description="获取单个系统设置")
    async def get_setting(key: str) -> str:
        """获取指定配置项"""
        async with async_session_factory() as db:
            from app.models.setting import Setting
            from sqlalchemy import select
            result = await db.execute(select(Setting).where(Setting.key == key))
            setting = result.scalar_one_or_none()
            if not setting:
                return json.dumps({"error": f"设置 '{key}' 不存在"})
            return json.dumps({key: setting.value}, ensure_ascii=False)

    @mcp.tool(description="更新或新增系统设置")
    async def update_setting(key: str, value: str) -> str:
        """新增/更新配置项"""
        async with async_session_factory() as db:
            from app.models.setting import Setting
            from sqlalchemy import select
            result = await db.execute(select(Setting).where(Setting.key == key))
            setting = result.scalar_one_or_none()
            if setting:
                setting.value = value
            else:
                setting = Setting(key=key, value=value)
                db.add(setting)
            await db.commit()
            return json.dumps({"message": f"设置 '{key}' 已更新", key: value}, ensure_ascii=False)

    @mcp.tool(description="获取系统当前状态（活跃卡片数、队列长度等）")
    async def get_system_status() -> str:
        """获取系统运行状态"""
        from app.services.agent_engine import agent_engine
        from app.models.card import Card
        from sqlalchemy import select, func
        async with async_session_factory() as db:
            running = await db.execute(
                select(func.count(Card.id)).where(Card.status == "running"))
            pending = await db.execute(
                select(func.count(Card.id)).where(Card.status == "pending"))
            waiting = await db.execute(
                select(func.count(Card.id)).where(Card.status == "waiting_approval"))
            blocked = await db.execute(
                select(func.count(Card.id)).where(Card.status == "blocked"))
            return json.dumps({
                "active_processes": agent_engine.process_count,
                "max_concurrent": 3,  # from settings
                "pending_cards": pending.scalar() or 0,
                "running_cards": running.scalar() or 0,
                "waiting_approval": waiting.scalar() or 0,
                "blocked_cards": blocked.scalar() or 0,
                "timestamp": _now(),
            }, ensure_ascii=False)

    return mcp
