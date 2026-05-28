from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schedule import Schedule, ScheduleLog
from app.services.schedule_engine import schedule_engine
from app.schemas.schedule import (
    ScheduleCreate, ScheduleUpdate, ScheduleResponse, ScheduleLogResponse,
)

router = APIRouter(prefix="/api")


@router.get("/schedules", response_model=list[ScheduleResponse])
async def list_schedules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Schedule).order_by(Schedule.created_at))
    schedules = result.scalars().all()
    return [
        ScheduleResponse(
            id=s.id, name=s.name, description=s.description or "",
            cron_expr=s.cron_expr, enabled=s.enabled,
            card_title=s.card_title, card_content=s.card_content or "",
            card_model=s.card_model, target_kanban_id=s.target_kanban_id,
            target_swimlane_id=s.target_swimlane_id,
            next_run_time=schedule_engine.get_next_run_time(s.id),
            created_at=s.created_at, updated_at=s.updated_at,
        ) for s in schedules
    ]


@router.post("/schedules", response_model=ScheduleResponse, status_code=201)
async def create_schedule(data: ScheduleCreate, db: AsyncSession = Depends(get_db)):
    import uuid
    from datetime import datetime, timezone

    # 验证 cron 表达式
    try:
        from apscheduler.triggers.cron import CronTrigger
        CronTrigger.from_crontab(data.cron_expr)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"无效的 cron 表达式: {e}")

    schedule = Schedule(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        cron_expr=data.cron_expr,
        enabled=1,
        card_title=data.card_title,
        card_content=data.card_content,
        card_model=data.card_model,
        target_kanban_id=data.target_kanban_id,
        target_swimlane_id=data.target_swimlane_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    await schedule_engine.add_schedule_job(schedule.id, schedule.cron_expr)

    return ScheduleResponse(
        id=schedule.id, name=schedule.name, description=schedule.description or "",
        cron_expr=schedule.cron_expr, enabled=schedule.enabled,
        card_title=schedule.card_title, card_content=schedule.card_content or "",
        card_model=schedule.card_model, target_kanban_id=schedule.target_kanban_id,
        target_swimlane_id=schedule.target_swimlane_id,
        next_run_time=schedule_engine.get_next_run_time(schedule.id),
        created_at=schedule.created_at, updated_at=schedule.updated_at,
    )


@router.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(schedule_id: str, data: ScheduleUpdate,
                           db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(schedule, key, value)
    await db.commit()
    await db.refresh(schedule)

    if schedule.enabled:
        await schedule_engine.add_schedule_job(schedule.id, schedule.cron_expr)

    return ScheduleResponse(
        id=schedule.id, name=schedule.name, description=schedule.description or "",
        cron_expr=schedule.cron_expr, enabled=schedule.enabled,
        card_title=schedule.card_title, card_content=schedule.card_content or "",
        card_model=schedule.card_model, target_kanban_id=schedule.target_kanban_id,
        target_swimlane_id=schedule.target_swimlane_id,
        next_run_time=schedule_engine.get_next_run_time(schedule.id),
        created_at=schedule.created_at, updated_at=schedule.updated_at,
    )


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    await schedule_engine.remove_schedule_job(schedule_id)
    await db.delete(schedule)
    await db.commit()
    return {"message": "定时任务已删除"}


@router.post("/schedules/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    schedule.enabled = 1 if schedule.enabled == 0 else 0
    await db.commit()

    if schedule.enabled:
        await schedule_engine.add_schedule_job(schedule.id, schedule.cron_expr)
    else:
        await schedule_engine.pause_schedule_job(schedule_id)

    return {"enabled": bool(schedule.enabled)}


@router.get("/schedules/{schedule_id}/logs", response_model=list[ScheduleLogResponse])
async def get_schedule_logs(schedule_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScheduleLog).where(ScheduleLog.schedule_id == schedule_id)
        .order_by(ScheduleLog.triggered_at.desc())
    )
    logs = result.scalars().all()
    return [
        ScheduleLogResponse(
            id=l.id, schedule_id=l.schedule_id, triggered_at=l.triggered_at,
            created_card_id=l.created_card_id, status=l.status,
            error_message=l.error_message, created_at=l.created_at,
        ) for l in logs
    ]
