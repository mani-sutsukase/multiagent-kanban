from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # 数据库
    database_url: str = f"sqlite+aiosqlite:///{(Path(__file__).parent.parent / 'data' / 'multiagent.db').as_posix()}"

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
