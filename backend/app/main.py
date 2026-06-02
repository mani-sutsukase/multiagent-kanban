import json
import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.staticfiles import StaticFiles
from sqlalchemy import select

from app.config import settings, _get_frontend_dist_path, _is_bundled
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
        tb_text = traceback.format_exc()
        print(tb_text)
        # 未知异常：将卡片设为 errored，写入失败原因
        async with async_session_factory() as db:
            db_card = await db.get(Card, card.id)
            if db_card and db_card.status == "running":
                db_card.status = "errored"
                db_card.result = f"任务执行失败：系统内部错误\n{tb_text[:2000]}"
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
from app.routers import kanbans, cards, approvals, logs, schedules, settings as settings_router, browse
app.include_router(kanbans.router)
app.include_router(cards.router)
app.include_router(approvals.router)
app.include_router(logs.router)
app.include_router(schedules.router)
app.include_router(settings_router.router)
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


@app.post("/api/restart")
async def restart_server():
    """触发 uvicorn --reload 热重启（touch main.py 文件时间戳）"""
    import os
    from pathlib import Path

    async def _do_restart():
        await asyncio.sleep(0.5)
        file_path = Path(__file__)
        os.utime(file_path, None)

    asyncio.create_task(_do_restart())
    return {"message": "服务器正在重启..."}


# ===== 生产模式：提供前端静态文件 =====
_frontend_dist = _get_frontend_dist_path()
if _frontend_dist:
    print(f"[main] 生产模式：前端静态文件来自 {_frontend_dist}")

    # 挂载 /assets/ 等静态资源
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="assets")

    # SPA 回落：所有非 API/WS 的路径返回 index.html
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # 不拦截 API 和 WebSocket 路径（FastAPI 路由优先匹配）
        if full_path.startswith("api/") or full_path.startswith("ws"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        index_path = _frontend_dist / "index.html"
        if index_path.exists():
            return HTMLResponse(index_path.read_text(encoding="utf-8"))
        return JSONResponse(status_code=404, content={"detail": "Frontend not built"})

    @app.get("/", include_in_schema=False)
    async def serve_spa_root():
        index_path = _frontend_dist / "index.html"
        if index_path.exists():
            return HTMLResponse(index_path.read_text(encoding="utf-8"))
        return JSONResponse(status_code=404, content={"detail": "Frontend not built"})
else:
    print("[main] 开发模式：前端由 Vite 开发服务器提供 (http://localhost:5173)")


# ===== 直接运行入口（用于 PyInstaller 打包的 EXE）=====
def run_server():
    """启动 uvicorn 服务器"""
    import uvicorn

    port = 8000
    # 支持通过命令行参数指定端口：MultiAgentKanban.exe --port 8080
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                try:
                    port = int(sys.argv[i + 1])
                except ValueError:
                    pass

    print(f"[main] MultiAgent Kanban 服务器启动于 http://localhost:{port}")
    print(f"[main] API 文档: http://localhost:{port}/docs")
    print(f"[main] 按 Ctrl+C 停止服务器")
    uvicorn.run(
        "app.main:app" if not _is_bundled() else app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=not _is_bundled(),  # 源码模式启用热重载，EXE 模式禁用
    )


if __name__ == "__main__":
    run_server()
