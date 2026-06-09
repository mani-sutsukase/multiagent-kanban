import sys
from pathlib import Path

from pydantic_settings import BaseSettings


def _is_bundled() -> bool:
    """检测是否运行在 PyInstaller 打包的 EXE 中"""
    return getattr(sys, 'frozen', False)


def _get_project_root() -> Path:
    """获取项目根目录（EXE 所在目录，或源码项目根目录）"""
    if _is_bundled():
        # PyInstaller 单文件模式：EXE 所在目录即为项目根
        return Path(sys.executable).parent.resolve()
    else:
        # 源码模式：backend/app/ -> backend/ -> 项目根
        return Path(__file__).parent.parent.parent.resolve()


def _get_frontend_dist_path() -> Path | None:
    """获取前端构建产物的路径（仅生产模式）"""
    if _is_bundled():
        # PyInstaller 会将 add-data 的文件解压到 _MEIPASS
        meipass = Path(sys._MEIPASS)
        dist_path = meipass / 'frontend' / 'dist'
        return dist_path if dist_path.exists() else None
    else:
        # 源码开发模式：项目根/frontend/dist
        dist_path = _get_project_root() / 'frontend' / 'dist'
        return dist_path if dist_path.exists() else None


def _get_default_db_path() -> str:
    """计算默认数据库路径（源码/EXE 统一使用项目根目录下的 data/）"""
    root = _get_project_root()
    data_dir = root / 'data'
    data_dir.mkdir(exist_ok=True)
    db_path = data_dir / 'multiagent.db'
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


class Settings(BaseSettings):
    # 数据库
    database_url: str = _get_default_db_path()

    # Agent 执行引擎
    max_concurrent_processes: int = 3
    claude_path: str = "claude"
    claude_git_bash_path: str = ""

    # 日志
    log_max_length: int = 100_000  # 单条日志最大字符数

    # WebSocket
    ws_heartbeat_interval: int = 30  # 秒

    # 定时任务
    schedule_misfire_grace_time: int = 60  # 秒

    model_config = {"env_prefix": "MULTIAGENT_", "env_file": ".env"}


settings = Settings()
