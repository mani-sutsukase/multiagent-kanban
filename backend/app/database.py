from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 迁移：为 swimlanes 表添加 local_path 列（如果不存在）
        await conn.run_sync(_add_swimlane_local_path)
        # 迁移：为 swimlanes 表添加 wait_for_reply 列（如果不存在）
        await conn.run_sync(_add_swimlane_wait_for_reply)
        # 迁移：为 cards 表添加 result 列（如果不存在）
        await conn.run_sync(_add_card_result_column)
        # 迁移：为 cards 表添加 last_prompt, last_output, user_reply 列（如果不存在）
        await conn.run_sync(_add_card_missing_columns)
        # 迁移：为 logs 表添加 prompt 列（如果不存在）
        await conn.run_sync(_add_log_prompt_column)
        # 迁移：为 cards 表添加 local_path 等字段
        await conn.run_sync(_add_card_path_fields)
        # 迁移：为 swimlanes 表添加 local_path_permission 等字段
        await conn.run_sync(_add_swimlane_path_fields)
        # 迁移：为 cards 表添加 dangerously_skip_permissions 列（如果不存在）
        await conn.run_sync(_add_card_dangerously_skip_permissions)
        # 迁移：为 cards 表添加 user_reply_question 列（如果不存在）
        await conn.run_sync(_add_card_user_reply_question)
        # 迁移：为 swimlanes 表添加 swimlane_type 列（如果不存在）
        await conn.run_sync(_add_swimlane_type_column)


def _add_swimlane_local_path(conn):
    """为已有数据库添加 local_path 列（幂等）"""
    from sqlalchemy import inspect
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("swimlanes")]
    if "local_path" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE swimlanes ADD COLUMN local_path VARCHAR"
            )
        )


def _add_card_result_column(conn):
    """为已有数据库添加 result 列（幂等）"""
    from sqlalchemy import inspect
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("cards")]
    if "result" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE cards ADD COLUMN result TEXT"
            )
        )


def _add_card_missing_columns(conn):
    """为已有数据库添加 last_prompt, last_output, user_reply 列（幂等）"""
    from sqlalchemy import inspect
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("cards")]
    for col_name in ("last_prompt", "last_output", "user_reply"):
        if col_name not in columns:
            conn.execute(
                __import__("sqlalchemy").text(
                    f"ALTER TABLE cards ADD COLUMN {col_name} TEXT"
                )
            )


def _add_swimlane_wait_for_reply(conn):
    """为已有数据库添加 wait_for_reply 列（幂等）"""
    from sqlalchemy import inspect
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("swimlanes")]
    if "wait_for_reply" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE swimlanes ADD COLUMN wait_for_reply VARCHAR NOT NULL DEFAULT '0'"
            )
        )


def _add_log_prompt_column(conn):
    """为已有数据库添加 prompt 列（幂等）"""
    from sqlalchemy import inspect
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("logs")]
    if "prompt" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE logs ADD COLUMN prompt TEXT"
            )
        )


def _add_card_path_fields(conn):
    """为已有数据库添加 local_path, local_path_permission, allowed_paths 列（幂等）"""
    from sqlalchemy import inspect
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("cards")]
    if "local_path" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE cards ADD COLUMN local_path VARCHAR"
            )
        )
    if "local_path_permission" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE cards ADD COLUMN local_path_permission VARCHAR NOT NULL DEFAULT 'read_write'"
            )
        )
    if "allowed_paths" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE cards ADD COLUMN allowed_paths TEXT NOT NULL DEFAULT '[]'"
            )
        )


def _add_swimlane_path_fields(conn):
    """为已有数据库添加 local_path_permission, allowed_paths 列（幂等）"""
    from sqlalchemy import inspect
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("swimlanes")]
    if "local_path_permission" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE swimlanes ADD COLUMN local_path_permission VARCHAR NOT NULL DEFAULT 'read_write'"
            )
        )
    if "allowed_paths" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE swimlanes ADD COLUMN allowed_paths TEXT NOT NULL DEFAULT '[]'"
            )
        )


def _add_card_dangerously_skip_permissions(conn):
    """为已有数据库添加 dangerously_skip_permissions 列（幂等）"""
    from sqlalchemy import inspect
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("cards")]
    if "dangerously_skip_permissions" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE cards ADD COLUMN dangerously_skip_permissions VARCHAR NOT NULL DEFAULT '0'"
            )
        )


def _add_card_user_reply_question(conn):
    """为已有数据库添加 user_reply_question 列（幂等）"""
    from sqlalchemy import inspect
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("cards")]
    if "user_reply_question" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE cards ADD COLUMN user_reply_question TEXT"
            )
        )


def _add_swimlane_type_column(conn):
    """为已有数据库添加 swimlane_type 列（幂等）"""
    from sqlalchemy import inspect
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("swimlanes")]
    if "swimlane_type" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE swimlanes ADD COLUMN swimlane_type VARCHAR NOT NULL DEFAULT 'normal'"
            )
        )
