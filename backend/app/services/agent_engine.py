import asyncio
import os
import re
import signal
import subprocess as _subprocess
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_factory
from app.models.card import Card
from app.models.kanban import Swimlane
from app.services.log_service import LogService
from app.services.card_engine import CardEngine
from app.websocket_manager import WebSocketManager


class AgentEngine:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_processes)
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._ws_manager: WebSocketManager | None = None
        self._claude_checked = False

    def set_ws_manager(self, ws_manager: WebSocketManager):
        self._ws_manager = ws_manager

    async def _ensure_claude_available(self):
        if self._claude_checked:
            return True
        try:
            check_env = os.environ.copy()
            if settings.claude_git_bash_path:
                check_env["CLAUDE_CODE_GIT_BASH_PATH"] = settings.claude_git_bash_path
            proc = await asyncio.create_subprocess_shell(
                f'"{settings.claude_path}" --version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=check_env,
            )
            await proc.communicate()
            self._claude_checked = proc.returncode == 0
            return self._claude_checked
        except FileNotFoundError:
            return False

    def _build_claude_args(self, card: Card, swimlane: Swimlane) -> list[str]:
        args = [settings.claude_path]
        if card.model:
            args.extend(["--model", card.model])
        prompt = swimlane.prompt
        if card.rejection_note:
            prompt += f"\n\n【上次审核意见】\n{card.rejection_note}\n\n请根据审核意见改进。"
        args.extend(["-p", prompt])
        if swimlane.skill:
            args.extend(["--skill", swimlane.skill])
        if card.session_id and card.status == "rejected":
            args.extend(["--resume", card.session_id])
        return args

    async def _extract_session_id(self, stdout: str) -> str | None:
        match = re.search(r"Session\s+(?:ID|id|Id)?\s*:?\s*(\S+)", stdout)
        if match:
            return match.group(1)
        return None

    async def _capture_output(self, log_id: str, card_id: str,
                               stream: asyncio.StreamReader, is_stderr: bool,
                               log_service: LogService):
        while True:
            line = await stream.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace")
            if is_stderr:
                await log_service.append_output(log_id, stderr=text)
            else:
                await log_service.append_output(log_id, stdout=text)
            if self._ws_manager:
                await self._ws_manager.broadcast({
                    "type": "card_log_update",
                    "card_id": card_id,
                    "log_id": log_id,
                    "stdout": text if not is_stderr else "",
                    "stderr": text if is_stderr else "",
                    "append": True,
                })

    async def _on_process_exit(self, card_id: str, swimlane_id: str, log_id: str,
                                exit_code: int, attempt: int):
        finished_at = datetime.now(timezone.utc).isoformat()
        async with async_session_factory() as db:
            log_service = LogService(db)
            await log_service.update_log(log_id, exit_code=exit_code, finished_at=finished_at)
            card_engine = CardEngine(db)
            card = await card_engine.card_service.get_card(card_id)
            if not card:
                return
            if exit_code == 0:
                await card_engine.handle_swimlane_completion(card)
                if self._ws_manager:
                    await self._ws_manager.broadcast({
                        "type": "card_status_changed",
                        "card_id": card_id,
                        "status": card.status,
                        "swimlane_id": card.current_swimlane_id,
                    })
                    if card.status == "waiting_approval":
                        await self._ws_manager.broadcast({
                            "type": "card_needs_approval",
                            "card_id": card_id,
                            "swimlane_id": swimlane_id,
                            "log_id": log_id,
                        })
                    elif card.status == "completed":
                        await self._ws_manager.broadcast({
                            "type": "card_completed",
                            "card_id": card_id,
                            "swimlane_id": None,
                        })
            else:
                card.status = "blocked"
                await db.commit()
                if self._ws_manager:
                    await self._ws_manager.broadcast({
                        "type": "card_status_changed",
                        "card_id": card_id,
                        "status": "blocked",
                        "swimlane_id": swimlane_id,
                    })

    async def execute_card(self, card: Card, swimlane: Swimlane):
        async with self.semaphore:
            if not await self._ensure_claude_available():
                async with async_session_factory() as db:
                    card = await db.get(Card, card.id)
                    if card:
                        card.status = "blocked"
                        await db.commit()
                return
            args = self._build_claude_args(card, swimlane)
            cmd = _subprocess.list2cmdline(args)
            # 构建子进程环境变量（继承父进程 + 自定义变量）
            proc_env = os.environ.copy()
            if settings.claude_git_bash_path:
                proc_env["CLAUDE_CODE_GIT_BASH_PATH"] = settings.claude_git_bash_path
            # 如果泳道配置了本地路径，则在该目录下启动 Claude（使用该目录的 claude 配置）
            cwd = swimlane.local_path if swimlane.local_path else None
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=proc_env,
                cwd=cwd,
            )
            self._processes[card.id] = proc
            async with async_session_factory() as db:
                log_service = LogService(db)
                logs = await log_service.get_card_logs(card.id)
                swimlane_logs = [l for l in logs if l.swimlane_id == swimlane.id]
                attempt = len(swimlane_logs) + 1
                log_entry = await log_service.create_log(
                    card_id=card.id, swimlane_id=swimlane.id,
                    attempt=attempt, process_id=proc.pid,
                )
            async with async_session_factory() as db:
                log_service = LogService(db)
                await asyncio.gather(
                    self._capture_output(log_entry.id, card.id, proc.stdout, False, log_service),
                    self._capture_output(log_entry.id, card.id, proc.stderr, True, log_service),
                )
            exit_code = await proc.wait()
            self._processes.pop(card.id, None)

            # 从 stdout 中提取 Claude session_id 并保存到日志
            async with async_session_factory() as db:
                ls = LogService(db)
                log_record = await ls.get_log(log_entry.id)
                if log_record and log_record.stdout:
                    session_id = await self._extract_session_id(log_record.stdout)
                    if session_id:
                        await ls.update_log(log_entry.id, session_id=session_id)

            await self._on_process_exit(card.id, swimlane.id, log_entry.id, exit_code, attempt)

    async def terminate_card(self, card_id: str):
        proc = self._processes.get(card_id)
        if proc and proc.returncode is None:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5)
            except (asyncio.TimeoutError, ProcessLookupError):
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass
            self._processes.pop(card_id, None)

    @property
    def process_count(self) -> int:
        return len(self._processes)


# 全局单例
agent_engine = AgentEngine()
