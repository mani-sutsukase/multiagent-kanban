import asyncio
import json
import os
import re
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Python 3.14+ on Windows 默认已使用 ProactorEventLoop，无需显式设置
# 但 create_subprocess_shell 在后台 Task 中可能失败，改用 to_thread + Popen

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_factory
from app.models.card import Card
from app.models.kanban import Swimlane
from app.services.log_service import LogService
from app.services.card_engine import CardEngine
from app.services.file_writer import (
    NO_FILE_TOOLS_INSTRUCTION,
    scan_directories,
    extract_file_sections,
    write_files,
)
from app.websocket_manager import WebSocketManager


# Claude 输出中表示执行失败的模式（权限问题、文件访问错误等）
_EXECUTION_FAILURE_PATTERNS = [
    re.compile(r"permission\s+denied", re.IGNORECASE),
    re.compile(r"access\s+denied", re.IGNORECASE),
    re.compile(r"cannot\s+access", re.IGNORECASE),
    re.compile(r"(?:is\s+)?not\s+(?:allowed|writable|accessible)", re.IGNORECASE),
    re.compile(r"cannot\s+(?:write|create|open|read)\s", re.IGNORECASE),
    re.compile(r"没有权限"),
    re.compile(r"拒绝访问"),
    re.compile(r"权限不足"),
    re.compile(r"无权访问"),
    re.compile(r"无法写入"),
    re.compile(r"无法创建"),
    re.compile(r"无法访问"),
    re.compile(r"EACCES"),
    re.compile(r"EPERM"),
]


def _clean_stderr_for_output(text: str) -> str:
    """清理 stderr 中的框架噪声（ANSI 控制码、spinner 动画、进度条），
    只保留有实际意义的错误/警告/状态文本。
    """
    if not text:
        return ""
    # 1. 去掉 ANSI 转义序列：颜色、光标移动、擦除行等
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
    text = re.sub(r'\x1b\][0-9;]*[a-zA-Z]', '', text)
    text = re.sub(r'\x1b[\[\]\(][?0-9;]*[a-zA-Z]?', '', text)
    # 2. 去掉转义的 Unicode 控制字符
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    # 3. 去掉只有 spinner 字符 + 常见状态文本的行
    #    spinner 字符范围: \u2800-\u28FF (Braille Patterns)
    spinner_line = re.compile(
        r'^[\s\u2800-\u28ff]*'
        r'(?:Thinking|Reading|Writing|Analyzing|Searching|Processing'
        r'|Generating|Compiling|Running|Waiting|Loading|Working|\.\.\.)?'
        r'[\s\u2800-\u28ff]*$'
    )
    lines = text.split('\n')
    cleaned = [l for l in lines if l.strip() and not spinner_line.match(l.strip())]
    return '\n'.join(cleaned)


def _detect_execution_failure(text: str) -> bool:
    """检测 Claude 的输出中是否包含执行失败/权限错误的指示

    即使 exit_code 为 0，Claude 也可能实际遇到错误（如无法读写文件），
    需要检查输出内容来判定。
    """
    if not text or not text.strip():
        return False
    # 只检查最后 3000 字符（最近的交互/错误部分）
    tail = text[-3000:] if len(text) > 3000 else text
    for pattern in _EXECUTION_FAILURE_PATTERNS:
        if pattern.search(tail):
            return True
    return False


def _extract_failure_reason(log_record, fallback_text: str = "") -> str:
    """从日志记录或输出文本中提取失败原因"""
    failure_msg = "任务执行失败"
    source_text = ""
    if log_record and log_record.stderr:
        source_text = log_record.stderr
    elif log_record and log_record.stdout:
        source_text = log_record.stdout
    elif fallback_text:
        source_text = fallback_text

    if source_text:
        lines = source_text.strip().split("\n")
        error_lines = [l for l in lines if l.strip()][-5:]
        error_text = "\n".join(error_lines)
        if len(error_text) > 500:
            error_text = error_text[-500:]
        if error_text.strip():
            failure_msg += f"\n{error_text.strip()}"
    return failure_msg


# 追加到泳道提示词末尾的回复标记指令（当 wait_for_reply="1" 时自动注入）
_REPLY_MARKER_INSTRUCTION = """

【回复标记指令】
如果你需要向用户提问、确认方向或请求用户输入才能继续工作，
请在你的完整回复内容之后（所有内容的末尾），单独输出以下 JSON 对象：

{"__requires_reply__": true, "__question__": "你具体要问用户的问题"}

如果不需要用户输入，请不要包含此 JSON 对象。
"""


def _save_swimlane_result(card_id: str, swimlane: "Swimlane", output_text: str) -> str | None:
    """将泳道的执行结果保存到磁盘文件，返回保存的绝对路径"""
    if not output_text or not output_text.strip():
        return None

    # backend/data/swimlane_results/{card_id}/
    # agent_engine.py -> backend/app/services/ -> backend/  (3 层 parent)
    backend_dir = Path(__file__).parent.parent.parent.resolve()
    results_dir = backend_dir / "data" / "swimlane_results" / card_id
    results_dir.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r'[\\/:*?"<>|]', '_', swimlane.name or f"swimlane_{swimlane.id}")
    filename = f"{swimlane.sort_order:03d}_{safe_name}.md"
    filepath = results_dir / filename

    filepath.write_text(output_text, encoding="utf-8")

    print(f"[agent_engine] 泳道结果已保存: {filepath}", flush=True)
    return str(filepath)


def _get_previous_swimlane_result_path(card_id: str, current_swimlane_sort_order: int) -> str | None:
    """查找上一泳道的执行结果文件路径

    在 data/swimlane_results/{card_id}/ 下查找文件名以
    (current_swimlane_sort_order - 1) 为前缀的文件。
    """
    if current_swimlane_sort_order <= 0:
        return None

    backend_dir = Path(__file__).parent.parent.parent.resolve()
    results_dir = backend_dir / "data" / "swimlane_results" / card_id
    if not results_dir.is_dir():
        return None

    prev_order = current_swimlane_sort_order - 1
    prefix = f"{prev_order:03d}_"
    for fname in results_dir.iterdir():
        if fname.name.startswith(prefix):
            return str(fname)
    return None


def _detect_reply_request_from_json(text: str) -> tuple[bool, str]:
    """从 Claude 输出中解析 JSON 回复请求标记

    扫描输出中的 JSON 对象，查找 __requires_reply__ 字段。
    返回 (是否需要回复, 问题内容)
    """
    if not text or not text.strip():
        return False, ""
    tail = text[-5000:] if len(text) > 5000 else text
    # 查找所有包含 __requires_reply__ 的 JSON 对象
    for match in re.finditer(
        r'\{\s*"[^"]*__requires_reply__[^}]*\}', tail, re.DOTALL
    ):
        try:
            obj = json.loads(match.group())
            if obj.get("__requires_reply__") is True:
                question = obj.get("__question__", "")
                return True, question
        except json.JSONDecodeError:
            continue
    return False, ""


def _strip_reply_marker(text: str) -> str:
    """从输出文本中移除回复标记 JSON 对象，保留 Claude 的实际回复内容"""
    if not text:
        return text
    return re.sub(
        r'\{\s*"[^"]*__requires_reply__[^}]*\}',
        '',
        text,
        flags=re.DOTALL,
    ).strip()


class AgentEngine:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_processes)
        self._processes: dict[str, subprocess.Popen] = {}
        self._ws_manager: WebSocketManager | None = None
        self._claude_checked = False
        self._junctions: dict[str, list[str]] = {}  # card_id -> [junction_paths]
        self._file_dirs: dict[str, list[str]] = {}  # card_id -> [rw_paths]

    def set_ws_manager(self, ws_manager: WebSocketManager):
        self._ws_manager = ws_manager

    def _is_path_within_cwd(self, target_path: str, cwd_path: str) -> bool:
        """检查 target_path 是否是 cwd_path 的子目录"""
        try:
            abs_target = os.path.abspath(target_path)
            abs_cwd = os.path.abspath(cwd_path)
            # 相同路径或在 cwd 的子目录下
            if abs_target == abs_cwd:
                return True
            return abs_target.startswith(abs_cwd.rstrip('\\') + '\\')
        except Exception:
            return False

    def _create_junction(self, link: str, target: str) -> bool:
        """在 Windows 上创建目录联接点 (junction)，使 target 可通过 link 访问"""
        try:
            os.makedirs(os.path.dirname(link), exist_ok=True)
            if os.path.exists(link):
                return True
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", link, target],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                print(f"[agent_engine] 已创建目录联接: {link} -> {target}", flush=True)
                return True
            else:
                print(f"[agent_engine] 创建目录联接失败: {result.stderr.strip()}", flush=True)
                return False
        except Exception as e:
            print(f"[agent_engine] 创建目录联接异常: {e}", flush=True)
            return False

    def _remove_junction(self, path: str):
        """安全删除目录联接点，不影响目标目录"""
        if not os.path.exists(path):
            return
        try:
            os.rmdir(path)
            print(f"[agent_engine] 已删除目录联接: {path}", flush=True)
        except Exception:
            try:
                subprocess.run(
                    ["cmd", "/c", "rmdir", path],
                    capture_output=True, timeout=5
                )
            except Exception:
                pass

    def _cleanup_card_junctions(self, card_id: str):
        """清理某张卡片创建的所有目录联接"""
        paths = self._junctions.pop(card_id, [])
        for p in paths:
            self._remove_junction(p)

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
        """构建 claude 命令行参数，返回 (args, full_prompt)

        提示词通过 stdin 管道传递（避免 Windows cmd.exe 编码破坏中文），
        因此 args 中不包含 -p 参数。
        """
        args = [settings.claude_path]
        if card.model:
            args.extend(["--model", card.model])
        # 跳过文件权限限制：Claude 可读写项目根目录及常见系统目录下的文件
        if getattr(card, 'dangerously_skip_permissions', None) == "1":
            args.append("--dangerously-skip-permissions")

        parts = []

        # 1. 卡片信息（始终包含）
        card_info = f"【任务信息】\n卡片标题：{card.title}"
        if card.content:
            card_info += f"\n卡片内容：{card.content}"
        parts.append(card_info)

        # 2. 泳道指令
        if swimlane.prompt and swimlane.prompt.strip():
            parts.append(f"\n\n【任务指令】\n{swimlane.prompt}")
        # 2b. 回复标记指令（Claude 可通过 JSON 显式声明需要用户回复）
        parts.append(_REPLY_MARKER_INSTRUCTION)
        # 2c. 禁用文件操作工具指令（避免 BashTool pre-flight 超时导致文件操作不可用）
        parts.append(NO_FILE_TOOLS_INSTRUCTION)

        # 2d. 上一泳道的执行结果路径（仅当存在时）
        prev_result_path = _get_previous_swimlane_result_path(card.id, swimlane.sort_order)
        if prev_result_path:
            parts.append(
                f"\n\n【上一泳道的执行结果】\n上一泳道完成后的完整输出已保存至：\n{prev_result_path}\n\n"
                f"你可以使用文件工具读取该文件，了解上一泳道的执行情况。"
            )

        # 2e. 编排泳道：注入 MCP 服务器和编排指令
        if getattr(swimlane, 'swimlane_type', 'normal') == 'orchestrator':
            # 添加 --mcp-servers 参数
            import json as _json
            mcp_config = _json.dumps({
                "kanban-mcp": {
                    "url": "http://127.0.0.1:8000/mcp"
                }
            })
            args.extend(["--mcp-servers", mcp_config])

            # 注入编排指令
            parts.append(
                "\n\n【编排任务指令】\n"
                "你是一个看板编排 Agent。你可以通过 MCP 工具调用看板系统的所有 API。\n"
                "可用的工具包括：创建/查看看板、管理泳道、创建/查看/移动卡片、审批/驳回卡片、\n"
                "回复等待回复的卡片、管理定时任务、修改系统设置、查看系统状态等。\n"
                "请根据当前看板状态和任务目标，自主决策并执行操作。\n"
                "所有工具已通过 MCP 协议注入，你可以直接调用它们。\n"
            )

        # 3. 审核意见（仅当存在时）
        if card.rejection_note:
            parts.append(
                f"\n\n【上次审核意见】\n{card.rejection_note}\n\n请根据审核意见改进。"
            )

        # 4. 用户回复（仅当存在时）
        if card.user_reply:
            parts.append(
                f"\n\n【用户回复】\n{card.user_reply}\n\n请根据用户的回复继续工作。"
            )

        # 如果有 session_id 且有用户回复（授权审批或等待回复），使用 --resume 恢复会话
        # 这样 Claude 能保留上次的对话上下文，知道之前卡在哪个文件操作上
        if card.session_id and card.user_reply:
            args.extend(["--resume", card.session_id])
            # 使用 --resume 时，stdin 内容作为恢复会话中的用户消息
            # 只需发送用户回复，不需要重复任务指令（已在原会话中）
            prompt = card.user_reply
        else:
            prompt = "".join(parts)
            # 提示词通过 stdin 传递，不在命令行参数中包含 -p（避免编码问题）
            if swimlane.skill:
                args.extend(["--skill", swimlane.skill])
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

            # 合并 stdout + 清理后的 stderr 作为卡片输出（用于错误检测和用户输入检测）
            # 注意：原始 stderr 在日志中完整保留（含 ANSI 码和 spinner），
            # 这里只清理掉框架噪声，保留有意义的错误/警告信息
            combined_output = ""
            if log_record:
                cleaned_stderr = _clean_stderr_for_output(log_record.stderr or "")
                combined_output = (log_record.stdout or "") + "\n" + cleaned_stderr
            else:
                combined_output = stdout_text or ""

            # 如果卡片已被手动终止（blocked），只保存输出和日志，不再覆盖状态
            if card.status == "blocked":
                card.last_output = combined_output
                await db.commit()
                return

            # 保存 claude 输出到卡片
            card.last_output = combined_output

            # ===== 状态判断：优先级从高到低 =====

            # 1. JSON 回复标记检测（唯一方式，Claude 通过 JSON 显式声明是否需要回复）
            reply_json_detected = False
            reply_question = ""
            if exit_code == 0:
                reply_json_detected, reply_question = _detect_reply_request_from_json(card.last_output or "")

            if reply_json_detected:
                # JSON 显式声明需要回复 → 进入 waiting_for_reply
                # 不清除 user_reply、result，保留现场给用户查看
                card.status = "waiting_for_reply"
                card.user_reply_question = reply_question or None
                # 从输出中移除 JSON 标记，用户只看到 Claude 的实际回复
                card.last_output = _strip_reply_marker(card.last_output)
                await db.commit()
                if self._ws_manager:
                    await self._ws_manager.broadcast({
                        "type": "card_status_changed",
                        "card_id": card_id,
                        "status": "waiting_for_reply",
                        "swimlane_id": swimlane_id,
                        "last_output": card.last_output,
                        "user_reply_question": card.user_reply_question,
                    })

            # 2. 执行错误检测（exit_code=0 但输出包含执行错误）
            elif exit_code == 0 and _detect_execution_failure(card.last_output or ""):
                failure_msg = _extract_failure_reason(log_record, card.last_output or "")
                card.result = failure_msg
                card.status = "errored"
                await db.commit()
                if self._ws_manager:
                    await self._ws_manager.broadcast({
                        "type": "card_status_changed",
                        "card_id": card_id,
                        "status": "errored",
                        "swimlane_id": swimlane_id,
                        "result": card.result,
                        "last_output": card.last_output,
                    })

            # 3. exit_code=0 正常执行成功 → 自动流转（不因 wait_for_reply 无条件暂停）
            #    只有 Priority 1 中 Claude 通过 JSON 标记显式请求回复才进入 waiting_for_reply
            elif exit_code == 0:
                card.result = "任务执行成功"
                card.user_reply = None
                card.user_reply_question = None  # 清除旧的回复标记
                await db.commit()
                await db.refresh(card)

                # 保存当前泳道的执行结果到磁盘，供后续泳道读取
                swimlane_obj = await db.get(Swimlane, swimlane_id)
                if swimlane_obj and card.last_output:
                    _save_swimlane_result(card_id, swimlane_obj, card.last_output)

                await card_engine.handle_swimlane_completion(card)
                broadcast_status = card.status

                # 从 Claude 输出中提取文件内容并写入磁盘
                allowed_dirs = self._file_dirs.pop(card_id, [])
                if allowed_dirs and card.last_output:
                    sections = extract_file_sections(card.last_output)
                    if sections:
                        results = write_files(sections, allowed_dirs)
                        written = [r for r in results if r.get("status") == "ok"]
                        if written:
                            paths_str = "; ".join(r["path"] for r in written)
                            print(f"[agent_engine] 已写入 {len(written)} 个文件: {paths_str}", flush=True)

                if self._ws_manager:
                    await self._ws_manager.broadcast({
                        "type": "card_status_changed",
                        "card_id": card_id,
                        "status": broadcast_status,
                        "swimlane_id": card.current_swimlane_id,
                        "result": card.result,
                        "last_output": card.last_output,
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

            # 4. exit_code != 0 → 进程异常退出，执行失败
            else:
                failure_msg = _extract_failure_reason(log_record, card.last_output or "")
                card.result = failure_msg
                card.status = "errored"
                await db.commit()
                if self._ws_manager:
                    await self._ws_manager.broadcast({
                        "type": "card_status_changed",
                        "card_id": card_id,
                        "status": "errored",
                        "swimlane_id": swimlane_id,
                        "result": card.result,
                        "last_output": card.last_output,
                    })

    async def execute_card(self, card: Card, swimlane: Swimlane):
        async with self.semaphore:
            available, check_error = await self._ensure_claude_available()
            if not available:
                claude_error = f"任务执行失败\n{check_error}"
                async with async_session_factory() as db:
                    db_card = await db.get(Card, card.id)
                    if db_card:
                        db_card.status = "errored"
                        db_card.result = claude_error
                        await db.commit()
                if self._ws_manager:
                    await self._ws_manager.broadcast({
                        "type": "card_status_changed",
                        "card_id": card.id,
                        "status": "errored",
                        "swimlane_id": swimlane.id,
                        "result": claude_error,
                    })
                return
            # 如果泳道提示词为空且不是编排泳道，跳过该泳道
            is_orchestrator = getattr(swimlane, 'swimlane_type', 'normal') == 'orchestrator'
            if not is_orchestrator and (not swimlane.prompt or not swimlane.prompt.strip()):
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

            # ---- 路径权限合并 ----
            all_allowed_paths = []

            # 卡片路径
            card_local = getattr(card, 'local_path', None) or ''
            if card_local.strip():
                perm = getattr(card, 'local_path_permission', 'read_write') or 'read_write'
                all_allowed_paths.append({"path": card_local.strip(), "permission": perm})
            card_extra = getattr(card, 'allowed_paths', None) or '[]'
            if card_extra.strip():
                try:
                    extra = json.loads(card_extra)
                    if isinstance(extra, list):
                        all_allowed_paths.extend(extra)
                except (json.JSONDecodeError, TypeError):
                    pass

            # 泳道路径
            swim_local = swimlane.local_path or ''
            if swim_local.strip():
                sw_perm = getattr(swimlane, 'local_path_permission', 'read_write') or 'read_write'
                all_allowed_paths.append({"path": swim_local.strip(), "permission": sw_perm})
            sw_extra = getattr(swimlane, 'allowed_paths', None) or '[]'
            if sw_extra.strip():
                try:
                    extra = json.loads(sw_extra)
                    if isinstance(extra, list):
                        all_allowed_paths.extend(extra)
                except (json.JSONDecodeError, TypeError):
                    pass

            # 去重（按路径去重，保留最后一个的权限设置）
            seen = {}
            for item in all_allowed_paths:
                seen[item["path"]] = item["permission"]
            unique_paths = [{"path": p, "permission": perm} for p, perm in seen.items()]

            # 设置 cwd：卡片 local_path > 泳道 local_path > None
            cwd = card_local.strip() or swim_local.strip() or None

            # ---- 创建目录联接点，使外部读写路径可作为 cwd 子目录访问 ----
            # 映射表：原始路径 -> 可在提示词中使用的实际路径（优先使用联接路径）
            path_display_map = {}
            if cwd:
                for item in unique_paths:
                    if item["permission"] == "read_write" and not self._is_path_within_cwd(item["path"], cwd):
                        target = item["path"]
                        try:
                            # 从目标路径生成安全的目录名
                            safe_name = re.sub(r'[\\/:*?"<>|]', '_', target.replace('\\', '_').replace(':', ''))
                            safe_name = f"__{safe_name}__"
                            junction_path = os.path.join(cwd, safe_name)
                            if self._create_junction(junction_path, target):
                                self._junctions.setdefault(card.id, []).append(junction_path)
                                path_display_map[target] = junction_path
                                continue
                        except Exception as e:
                            print(f"[agent_engine] 目录联接处理失败 {item['path']}: {e}", flush=True)
                    # 如果无需联接（已在 cwd 内）或联接失败，使用原路径
                    path_display_map[item["path"]] = item["path"]

            cmd = subprocess.list2cmdline(args)

            # 构建子进程环境变量（继承父进程 + 自定义变量）
            proc_env = os.environ.copy()
            if settings.claude_git_bash_path:
                proc_env["CLAUDE_CODE_GIT_BASH_PATH"] = settings.claude_git_bash_path
            # 构建 CLAUDE_CODE_ALLOWED_PATHS 环境变量（原始路径，供 claude 参考）
            if unique_paths:
                path_list = [p["path"] for p in unique_paths]
                proc_env["CLAUDE_CODE_ALLOWED_PATHS"] = ";".join(path_list)
            # 为路径权限追加提示词说明（明确告知 Claude 哪些目录可读写、哪些仅可读）
            rw_paths = [p["path"] for p in unique_paths if p["permission"] == "read_write"]
            ro_paths = [p["path"] for p in unique_paths if p["permission"] == "read_only"]
            if rw_paths or ro_paths:
                path_note = "\n\n【文件访问说明】\n"
                if rw_paths:
                    path_note += "以下路径允许读写访问，你可以在此目录下读取和修改文件：\n"
                    for p in rw_paths:
                        display_path = path_display_map.get(p, p)
                        suffix = f" (原始路径: {p})" if display_path != p else ""
                        path_note += f"- {display_path}{suffix}\n"
                    path_note += "\n"
                if ro_paths:
                    path_note += "以下路径仅允许读取，不允许修改任何文件：\n"
                    for p in ro_paths:
                        path_note += f"- {p}\n"
                full_prompt += path_note
            # 扫描读写目录，将现有文件列表注入提示词（替代 Claude 的 ReadTool）
            if rw_paths:
                dir_context = scan_directories(rw_paths)
                if dir_context:
                    full_prompt += f"\n\n【目录文件列表】\n{dir_context}"
            # 保存读写目录列表，供 _on_process_exit 中提取文件时使用
            self._file_dirs[card.id] = rw_paths
            # ---- 路径权限合并结束 ----

            # 保存完整提示词（含路径信息）到卡片，便于 UI 查看实际发送给 claude 的内容
            async with async_session_factory() as db:
                db_card = await db.get(Card, card.id)
                if db_card:
                    db_card.last_prompt = full_prompt
                    await db.commit()
            try:
                # 使用 to_thread + Popen 避免 Python 3.14 Windows 异步子进程问题
                # 提示词通过 stdin 管道传递为 UTF-8 字节，避免 Windows cmd.exe 编码破坏中文
                proc = await asyncio.to_thread(
                    subprocess.Popen,
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=proc_env,
                    cwd=cwd,
                    shell=True,
                )
                # 将提示词以 UTF-8 写入 stdin，然后关闭管道（Claude CLI 会读取 stdin 作为提示词）
                stdin_bytes = full_prompt.encode("utf-8")
                await asyncio.to_thread(proc.stdin.write, stdin_bytes)
                await asyncio.to_thread(proc.stdin.close)
                self._processes[card.id] = proc
                async with async_session_factory() as db:
                    log_service = LogService(db)
                    logs = await log_service.get_card_logs(card.id)
                    swimlane_logs = [l for l in logs if l.swimlane_id == swimlane.id]
                    attempt = len(swimlane_logs) + 1
                    log_entry = await log_service.create_log(
                        card_id=card.id, swimlane_id=swimlane.id,
                        attempt=attempt, process_id=proc.pid,
                        prompt=full_prompt,
                    )
                async with async_session_factory() as db:
                    log_service = LogService(db)
                    await asyncio.gather(
                        self._capture_output(log_entry.id, card.id, proc.stdout, False, log_service),
                        self._capture_output(log_entry.id, card.id, proc.stderr, True, log_service),
                    )
                exit_code = await asyncio.to_thread(proc.wait)
                self._processes.pop(card.id, None)

                # 从 stdout 中提取 Claude session_id 并保存到日志和卡片，同时获取完整输出
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
                                # 同时保存到 Card，后续 --resume 需要用到
                                card_obj = await db.get(Card, card_id)
                                if card_obj:
                                    card_obj.session_id = session_id
                                    await db.commit()

                await self._on_process_exit(card.id, swimlane.id, log_entry.id, exit_code, attempt, stdout_text)
            finally:
                # 无论成功还是异常，清理本次卡片创建的目录联接
                self._cleanup_card_junctions(card.id)

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
        self._cleanup_card_junctions(card_id)

    @property
    def process_count(self) -> int:
        return len(self._processes)


# 全局单例
agent_engine = AgentEngine()
