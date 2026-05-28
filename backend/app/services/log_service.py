from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log import Log


class LogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_log(self, card_id: str, swimlane_id: str, attempt: int = 1,
                         process_id: int = None, session_id: str = None) -> Log:
        log = Log(
            card_id=card_id,
            swimlane_id=swimlane_id,
            attempt=attempt,
            process_id=process_id,
            session_id=session_id,
            started_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def update_log(self, log_id: str, **kwargs) -> Log | None:
        result = await self.db.execute(
            update(Log).where(Log.id == log_id).values(**kwargs).returning(Log)
        )
        await self.db.commit()
        row = result.fetchone()
        if row:
            return row[0]
        return None

    async def append_output(self, log_id: str, stdout: str = None, stderr: str = None):
        log = await self.get_log(log_id)
        if not log:
            return
        updates = {}
        if stdout:
            updates["stdout"] = log.stdout + stdout
        if stderr:
            updates["stderr"] = log.stderr + stderr
        if updates:
            await self.db.execute(
                update(Log).where(Log.id == log_id).values(**updates)
            )
            await self.db.commit()

    async def get_log(self, log_id: str) -> Log | None:
        result = await self.db.execute(select(Log).where(Log.id == log_id))
        return result.scalar_one_or_none()

    async def get_card_logs(self, card_id: str) -> list[Log]:
        result = await self.db.execute(
            select(Log).where(Log.card_id == card_id).order_by(Log.started_at)
        )
        return list(result.scalars().all())
