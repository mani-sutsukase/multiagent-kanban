"""文件写入工具：替代 Claude 内部文件工具的方案。

在提示词中要求 Claude 仅输出文件内容（使用标记格式），
由本模块负责解析输出内容并写入磁盘。
"""

import os
import re
from pathlib import Path

# Claude 输出中文件内容块的起止标记
_FILE_START_RE = re.compile(r'【文件开始[：:]\s*(.+?)】')
_FILE_END_MARKER = "【文件结束】"


def scan_directories(paths: list[str]) -> str:
    """扫描目录，生成供提示词使用的文件列表上下文

    Args:
        paths: 要扫描的目录路径列表

    Returns:
        目录文件列表的文本描述
    """
    lines = []
    for base_path in paths:
        if not base_path or not os.path.isdir(base_path):
            continue
        rel_name = os.path.basename(base_path.rstrip("\\/"))
        files = sorted(os.listdir(base_path))
        lines.append(f"目录 {rel_name}/（{base_path}）现有文件：")
        for f in files:
            fp = os.path.join(base_path, f)
            if os.path.isfile(fp):
                size = os.path.getsize(fp)
                lines.append(f"  - {f}（{size} 字节）")
        if not files:
            lines.append(f"  （空目录）")
    return "\n".join(lines)


def extract_file_sections(text: str) -> list[dict]:
    """从 Claude 输出中解析文件内容块

    Claude 应使用以下格式标记文件内容：

        【文件开始：相对/路径/文件名.txt】
        文件内容...
        【文件结束】

    Args:
        text: Claude 的 stdout 文本

    Returns:
        [{"path": "相对/路径/文件名.txt", "content": "文件内容"}, ...]
    """
    if not text:
        return []

    sections = []
    pos = 0
    while True:
        match = _FILE_START_RE.search(text, pos)
        if not match:
            break

        file_path = match.group(1).strip()
        content_start = match.end()

        end_pos = text.find(_FILE_END_MARKER, content_start)
        if end_pos == -1:
            # 没有闭合标记，忽略这个不完整块
            break

        content = text[content_start:end_pos].strip("\r\n")
        if content:
            sections.append({"path": file_path, "content": content})
        pos = end_pos + len(_FILE_END_MARKER)

    return sections


def _resolve_target_path(file_path: str, allowed_dirs: list[str]) -> str | None:
    """将 Claude 输出的文件路径解析为绝对路径

    处理相对路径和绝对路径两种形式：
    - 相对路径（如 text/椰果.txt）→ 拼接在 allowed_dirs 下
    - 绝对路径（如 D:\\p\\codex-project\\text\\椰果.txt）→ 直接使用
    """
    p = Path(file_path)

    if p.is_absolute():
        return str(p)

    # 相对路径：在允许的目录下查找
    for base in allowed_dirs:
        candidate = Path(base) / p
        # 确保目标在允许目录范围内
        try:
            candidate.relative_to(Path(base).resolve())
            return str(candidate)
        except ValueError:
            continue

    # 没有匹配，仍使用第一个允许目录
    if allowed_dirs:
        return str(Path(allowed_dirs[0]) / p)
    return None


def write_files(sections: list[dict], allowed_dirs: list[str]) -> list[dict]:
    """将解析出的文件内容写入磁盘

    Args:
        sections: extract_file_sections 的返回结果
        allowed_dirs: 允许写入的目录列表

    Returns:
        [{"path": "写入的绝对路径", "size": 字节数, "status": "ok"|"skipped"}, ...]
    """
    results = []
    for sec in sections:
        target = _resolve_target_path(sec["path"], allowed_dirs)
        if not target:
            results.append({"path": sec["path"], "size": 0, "status": "skipped"})
            continue

        os.makedirs(os.path.dirname(target), exist_ok=True)
        content = sec["content"]
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)

        results.append({
            "path": target,
            "size": len(content.encode("utf-8")),
            "status": "ok",
        })
    return results


# 追加到提示词末尾的指令：禁止使用文件工具，改用标记格式
NO_FILE_TOOLS_INSTRUCTION = """

【文件操作说明】
注意：当前环境不支持 Read、Write、Edit、Bash 等文件操作工具。请勿尝试使用这些工具。

如果你需要创建或修改文件，请直接将文件内容输出到回复中，并使用以下格式包裹：

【文件开始：text/文件名.txt】
文件内容...
【文件结束】

系统会自动识别上述标记并将内容保存到对应文件。
文件名请使用相对路径（如 text/椰果.txt）。
"""
