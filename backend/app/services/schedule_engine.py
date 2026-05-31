import uuid
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.database import async_session_factory
from app.models.schedule import Schedule, ScheduleLog
from app.services.card_service import CardService
from app.websocket_manager import WebSocketManager


class ScheduleEngine:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._ws_manager: WebSocketManager | None = None

    def set_ws_manager(self, ws_manager: WebSocketManager):
        self._ws_manager = ws_manager

    async def start(self):
        self.scheduler.start()
        await self._load_enabled_schedules()

    async def stop(self):
        self.scheduler.shutdown(wait=False)

    async def _load_enabled_schedules(self):
        async with async_session_factory() as db:
            result = await db.execute(
                select(Schedule).where(Schedule.enabled == 1)
            )
            schedules = result.scalars().all()
            for s in schedules:
                self._add_job(s)

    def _add_job(self, schedule: Schedule):
        try:
            trigger = CronTrigger.from_crontab(schedule.cron_expr)
            self.scheduler.add_job(
                self._trigger_task,
                trigger=trigger,
                id=schedule.id,
                args=[schedule.id],
                replace_existing=True,
                misfire_grace_time=None,
            )
        except Exception as e:
            print(f"Failed to add job for schedule {schedule.id}: {e}")

    async def _create_card_from_template(self, schedule: Schedule) -> str | None:
        async with async_session_factory() as db:
            card_service = CardService(db)
            try:
                card = await card_service.create_card(
                    kanban_id=schedule.target_kanban_id,
                    title=schedule.card_title,
                    content=schedule.card_content,
                    model=schedule.card_model,
                    target_swimlane_id=schedule.target_swimlane_id,
                )
                return card.id
            except Exception as e:
                return None

    async def _log_execution(self, schedule_id: str, card_id: str | None,
                              status: str, error_message: str = None):
        async with async_session_factory() as db:
            log = ScheduleLog(
                id=str(uuid.uuid4()),
                schedule_id=schedule_id,
                triggered_at=datetime.now(timezone.utc).isoformat(),
                created_card_id=card_id,
                status=status,
                error_message=error_message,
            )
            db.add(log)
            await db.commit()

    async def _trigger_task(self, schedule_id: str):
        now = datetime.now(timezone.utc).isoformat()

        async with async_session_factory() as db:
            result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
            schedule = result.scalar_one_or_none()
            if not schedule or not schedule.enabled:
                return

        card_id = await self._create_card_from_template(schedule)
        if card_id:
            await self._log_execution(schedule_id, card_id, "success")
            if self._ws_manager:
                await self._ws_manager.broadcast({
                    "type": "schedule_triggered",
                    "schedule_id": schedule_id,
                    "card_id": card_id,
                    "kanban_id": schedule.target_kanban_id,
                })
        else:
            await self._log_execution(schedule_id, None, "failed",
                                      "创建卡片失败：看板或泳道可能已被删除")

    async def add_schedule_job(self, schedule_id: str, cron_expr: str):
        try:
            trigger = CronTrigger.from_crontab(cron_expr)
            self.scheduler.add_job(
                self._trigger_task,
                trigger=trigger,
                id=schedule_id,
                args=[schedule_id],
                replace_existing=True,
                misfire_grace_time=None,
            )
        except Exception as e:
            raise ValueError(f"无效的 cron 表达式: {e}")

    async def remove_schedule_job(self, schedule_id: str):
        if self.scheduler.get_job(schedule_id):
            self.scheduler.remove_job(schedule_id)

    async def pause_schedule_job(self, schedule_id: str):
        if self.scheduler.get_job(schedule_id):
            self.scheduler.pause_job(schedule_id)

    async def resume_schedule_job(self, schedule_id: str):
        if self.scheduler.get_job(schedule_id):
            self.scheduler.resume_job(schedule_id)

    def get_next_run_time(self, schedule_id: str) -> str | None:
        job = self.scheduler.get_job(schedule_id)
        if job and job.next_run_time:
            return job.next_run_time.isoformat()
        return None


# 全局单例
schedule_engine = ScheduleEngine()
