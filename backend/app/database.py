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
