import json
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.config import settings
from app.database import init_db, async_session_factory
from app.websocket_manager import WebSocketManager
from app.models.card import Card
from app.models.kanban import Swimlane
from app.models.setting import Setting
from app.services.schedule_engine import schedule_engine
from app.services.agent_engine import agent_engine

# 全局实例
ws_manager = WebSocketManager()
_card_picker_task: asyncio.Task | None = None


async def _reset_orphaned_cards():
    """服务器启动时，将上次残留的 running 卡片重置为 pending"""
    async with async_session_factory() as db:
        result = await db.execute(select(Card).where(Card.status == "running"))
        orphaned = result.scalars().all()
        for card in orphaned:
            card.status = "pending"
        await db.commit()
        if orphaned:
            print(f"[picker] 已重置 {len(orphaned)} 张孤儿卡片为 pending")


async def _safe_execute_card(card: Card, swimlane: Swimlane):
    """安全执行 Agent，确保异常不会导致卡片卡死在 running"""
    try:
        await agent_engine.execute_card(card, swimlane)
    except asyncio.CancelledError:
        # 服务器关闭时的取消，将卡片重置为 pending
        async with async_session_factory() as db:
            db_card = await db.get(Card, card.id)
            if db_card and db_card.status == "running":
                db_card.status = "pending"
                await db.commit()
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        # 未知异常：将卡片设为 blocked
        async with async_session_factory() as db:
            db_card = await db.get(Card, card.id)
            if db_card and db_card.status == "running":
                db_card.status = "blocked"
                await db.commit()


async def _get_polling_interval() -> int:
    """从数据库读取轮询间隔配置，默认 5 秒"""
    try:
        async with async_session_factory() as db:
            result = await db.execute(
                select(Setting).where(Setting.key == "polling_interval")
            )
            setting = result.scalar_one_or_none()
            if setting:
                return max(1, int(setting.value))
    except Exception:
        pass
    return 5


async def _card_picker_loop():
    """后台轮询任务：持续扫描 pending 卡片并启动 Agent 执行"""
    while True:
        try:
            async with async_session_factory() as db:
                result = await db.execute(
                    select(Card).where(Card.status == "pending")
                )
                pending_cards = result.scalars().all()
                for card in pending_cards:
                    swimlane = await db.get(Swimlane, card.current_swimlane_id)
                    if not swimlane:
                        continue
                    # 标记为运行中
                    card.status = "running"
                    await db.commit()
                    await db.refresh(card)
                    # 广播状态变更
                    await ws_manager.broadcast({
                        "type": "card_status_changed",
                        "card_id": card.id,
                        "status": "running",
                        "swimlane_id": card.current_swimlane_id,
                    })
                    # 安全异步启动 Agent 执行，不阻塞轮询
                    asyncio.create_task(_safe_execute_card(card, swimlane))
        except asyncio.CancelledError:
            break
        except Exception:
            import traceback
            traceback.print_exc()
        interval = await _get_polling_interval()
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    schedule_engine.set_ws_manager(ws_manager)
    agent_engine.set_ws_manager(ws_manager)
    await schedule_engine.start()

    # 重置上次残留的 running 卡片
    await _reset_orphaned_cards()

    # 启动卡片拾取器
    global _card_picker_task
    _card_picker_task = asyncio.create_task(_card_picker_loop())

    yield

    # 停止拾取器
    if _card_picker_task:
        _card_picker_task.cancel()
        try:
            await _card_picker_task
        except asyncio.CancelledError:
            pass
    await schedule_engine.stop()


app = FastAPI(
    title="MultiAgent Kanban",
    description="多 Agent 协作 Kanban 系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


# 注册 REST 路由
from app.routers import kanbans, cards, approvals, logs, schedules, settings, browse
app.include_router(kanbans.router)
app.include_router(cards.router)
app.include_router(approvals.router)
app.include_router(logs.router)
app.include_router(schedules.router)
app.include_router(settings.router)
app.include_router(browse.router)


# WebSocket 端点
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.ws_heartbeat_interval,
                )
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    pass
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
