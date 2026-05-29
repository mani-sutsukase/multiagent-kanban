import asyncio
import os
import re
import subprocess
import sys
import traceback
from datetime import datetime, timezone

# Python 3.14+ on Windows 默认已使用 ProactorEventLoop，无需显式设置
# 但 create_subprocess_shell 在后台 Task 中可能失败，改用 to_thread + Popen

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_factory
from app.models.card import Card
from app.models.kanban import Swimlane
from app.services.log_service import LogService
from app.services.card_engine import CardEngine
from app.websocket_manager import WebSocketManager
from app.services.kanban_service import SwimlaneService


class AgentEngine:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_processes)
        self._processes: dict[str, subprocess.Popen] = {}
        self._ws_manager: WebSocketManager | None = None
        self._claude_checked = False

    def set_ws_manager(self, ws_manager: WebSocketManager):
        self._ws_manager = ws_manager

    async def _ensure_claude_available(self) -> tuple[bool, str]:
        """检查 claude CLI 是否可用"""
        if self._claude_checked:
            return True, ""
        try:
            import sys as _sys
            check_env = os.environ.copy()
            if settings.claude_git_bash_path:
                check_env["CLAUDE_CODE_GIT_BASH_PATH"] = settings.claude_git_bash_path
            # 使用 to_thread + subprocess.run 替代 create_subprocess_shell
            # 避免 Windows + Python 3.14 下事件循环子进程的兼容问题
            print(f"[agent_engine] 正在检查 claude 可用性...", flush=True)
            print(f"[agent_engine] claude_path={settings.claude_path}, shell={_sys.platform == 'win32'}", flush=True)
            result = await asyncio.to_thread(
                subprocess.run,
                [settings.claude_path, "--version"],
                capture_output=True, text=True,
                env=check_env,
                shell=_sys.platform == "win32",
            )
            print(f"[agent_engine] claude 检查完成: returncode={result.returncode}", flush=True)
            self._claude_checked = result.returncode == 0
            if not self._claude_checked:
                return False, f"claude --version 返回非零退出码: {result.returncode}\n{result.stderr.strip()}"
            return True, ""
        except Exception as e:
            import traceback as _tb
            print(f"[agent_engine] claude 检查异常!", flush=True)
            _tb.print_exc()
            return False, f"检查 claude 可用性时出错: {type(e).__name__}: {e}"

    def _build_claude_args(self, card: Card, swimlane: Swimlane) -> tuple[list[str], str]:
        """构建 claude 命令行参数，返回 (args, full_prompt)"""
        args = [settings.claude_path]
        if card.model:
            args.extend(["--model", card.model])
        prompt = swimlane.prompt
        if card.rejection_note:
            prompt += f"\n\n【上次审核意见】\n{card.rejection_note}\n\n请根据审核意见改进。"
        if card.user_reply:
            prompt += f"\n\n【用户回复】\n{card.user_reply}\n\n请根据用户的回复继续工作。"
        args.extend(["-p", prompt])
        if swimlane.skill:
            args.extend(["--skill", swimlane.skill])
        if card.session_id and card.status == "rejected":
            args.extend(["--resume", card.session_id])
        return args, prompt

    async def _extract_session_id(self, stdout: str) -> str | None:
        match = re.search(r"Session\s+(?:ID|id|Id)?\s*:?\s*(\S+)", stdout)
        if match:
            return match.group(1)
        return None

    async def _capture_output(self, log_id: str, card_id: str,
                               stream, is_stderr: bool,
                               log_service: LogService):
        """读取子进程输出（支持 asyncio.StreamReader 或 subprocess.PIPE 文件对象）"""
        while True:
            if isinstance(stream, asyncio.StreamReader):
                line = await stream.readline()
            else:
                line = await asyncio.to_thread(stream.readline)
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
                                exit_code: int, attempt: int, stdout_text: str = ""):
        finished_at = datetime.now(timezone.utc).isoformat()
        async with async_session_factory() as db:
            log_service = LogService(db)
            await log_service.update_log(log_id, exit_code=exit_code, finished_at=finished_at)
            log_record = await log_service.get_log(log_id)
            card_engine = CardEngine(db)
            card = await card_engine.card_service.get_card(card_id)
            if not card:
                return

            # 保存 claude 输出到卡片
            card.last_output = stdout_text or (log_record.stdout if log_record else "")

            if exit_code == 0:
                card.result = "任务执行成功"
                # 清除 user_reply（已使用）
                card.user_reply = None
                await db.commit()
                await db.refresh(card)

                # 检查泳道是否配置了等待回复
                swimlane_svc = SwimlaneService(db)
                swimlane = await swimlane_svc.get(swimlane_id)
                wait_for_reply = swimlane.wait_for_reply == "1" if swimlane else False

                if wait_for_reply:
                    card.status = "waiting_for_reply"
                    await db.commit()
                    await db.refresh(card)
                    broadcast_status = "waiting_for_reply"
                else:
                    await card_engine.handle_swimlane_completion(card)
                    broadcast_status = card.status

                if self._ws_manager:
                    await self._ws_manager.broadcast({
                        "type": "card_status_changed",
                        "card_id": card_id,
                        "status": broadcast_status,
                        "swimlane_id": card.current_swimlane_id,
                        "result": card.result,
                    })
                    if broadcast_status == "waiting_approval":
                        await self._ws_manager.broadcast({
                            "type": "card_needs_approval",
                            "card_id": card_id,
                            "swimlane_id": swimlane_id,
                            "log_id": log_id,
                        })
                    elif broadcast_status == "completed":
                        await self._ws_manager.broadcast({
                            "type": "card_completed",
                            "card_id": card_id,
                            "swimlane_id": None,
                        })
            else:
                # 从 stderr 提取失败原因
                failure_msg = "任务执行失败"
                if log_record and log_record.stderr:
                    lines = log_record.stderr.strip().split("\n")
                    # 取最后几行非空错误信息，最多 500 字符
                    error_lines = [l for l in lines if l.strip()][-5:]
                    error_text = "\n".join(error_lines)
                    if len(error_text) > 500:
                        error_text = error_text[-500:]
                    if error_text.strip():
                        failure_msg += f"\n{error_text.strip()}"
                elif log_record and log_record.stdout:
                    lines = log_record.stdout.strip().split("\n")
                    error_lines = [l for l in lines if l.strip()][-5:]
                    error_text = "\n".join(error_lines)
                    if len(error_text) > 500:
                        error_text = error_text[-500:]
                    if error_text.strip():
                        failure_msg += f"\n{error_text.strip()}"
                card.result = failure_msg
                card.status = "blocked"
                await db.commit()
                if self._ws_manager:
                    await self._ws_manager.broadcast({
                        "type": "card_status_changed",
                        "card_id": card_id,
                        "status": "blocked",
                        "swimlane_id": swimlane_id,
                        "result": card.result,
                    })

    async def execute_card(self, card: Card, swimlane: Swimlane):
        async with self.semaphore:
            available, check_error = await self._ensure_claude_available()
            if not available:
                claude_error = f"任务执行失败\n{check_error}"
                async with async_session_factory() as db:
                    db_card = await db.get(Card, card.id)
                    if db_card:
                        db_card.status = "blocked"
                        db_card.result = claude_error
                        await db.commit()
                if self._ws_manager:
                    await self._ws_manager.broadcast({
                        "type": "card_status_changed",
                        "card_id": card.id,
                        "status": "blocked",
                        "swimlane_id": swimlane.id,
                        "result": claude_error,
                    })
                return
            # 如果泳道提示词为空，跳过该泳道，直接推进到下一泳道或完成
            if not swimlane.prompt or not swimlane.prompt.strip():
                async with async_session_factory() as db:
                    card_engine = CardEngine(db)
                    db_card = await db.get(Card, card.id)
                    if db_card:
                        db_card.result = "泳道提示词为空，自动跳过"
                        await db.commit()
                        await db.refresh(db_card)
                        await card_engine.handle_swimlane_completion(db_card)
                        if self._ws_manager:
                            await self._ws_manager.broadcast({
                                "type": "card_status_changed",
                                "card_id": card.id,
                                "status": db_card.status,
                                "swimlane_id": db_card.current_swimlane_id,
                            })
                return
            args, full_prompt = self._build_claude_args(card, swimlane)
            cmd = subprocess.list2cmdline(args)

            # 保存提示词到卡片
            async with async_session_factory() as db:
                db_card = await db.get(Card, card.id)
                if db_card:
                    db_card.last_prompt = full_prompt
                    await db.commit()
            # 构建子进程环境变量（继承父进程 + 自定义变量）
            proc_env = os.environ.copy()
            if settings.claude_git_bash_path:
                proc_env["CLAUDE_CODE_GIT_BASH_PATH"] = settings.claude_git_bash_path
            # 如果泳道配置了本地路径，则在该目录下启动 Claude（使用该目录的 claude 配置）
            cwd = swimlane.local_path if swimlane.local_path else None
            # 使用 to_thread + Popen 避免 Python 3.14 Windows 异步子进程问题
            proc = await asyncio.to_thread(
                subprocess.Popen,
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=proc_env,
                cwd=cwd,
                shell=True,
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
            exit_code = await asyncio.to_thread(proc.wait)
            self._processes.pop(card.id, None)

            # 从 stdout 中提取 Claude session_id 并保存到日志，同时获取完整输出
            stdout_text = ""
            async with async_session_factory() as db:
                ls = LogService(db)
                log_record = await ls.get_log(log_entry.id)
                if log_record:
                    if log_record.stdout:
                        stdout_text = log_record.stdout
                        session_id = await self._extract_session_id(log_record.stdout)
                        if session_id:
                            await ls.update_log(log_entry.id, session_id=session_id)

            await self._on_process_exit(card.id, swimlane.id, log_entry.id, exit_code, attempt, stdout_text)

    async def terminate_card(self, card_id: str):
        proc = self._processes.get(card_id)
        if proc and proc.returncode is None:
            try:
                proc.terminate()
                await asyncio.wait_for(asyncio.to_thread(proc.wait), timeout=5)
            except (asyncio.TimeoutError, ProcessLookupError):
                try:
                    proc.kill()
                    await asyncio.to_thread(proc.wait)
                except ProcessLookupError:
                    pass
            self._processes.pop(card_id, None)

    @property
    def process_count(self) -> int:
        return len(self._processes)


# 全局单例
agent_engine = AgentEngine()
