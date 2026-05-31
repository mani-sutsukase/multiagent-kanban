from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.card import Card
from app.models.kanban import Kanban
from app.models.log import Log
from app.services.log_service import LogService
from app.schemas.log import LogResponse, CardLogSummary

router = APIRouter(prefix="/api")


@router.get("/cards/{card_id}/logs", response_model=list[LogResponse])
async def get_card_logs(card_id: str, db: AsyncSession = Depends(get_db)):
    service = LogService(db)
    logs = await service.get_card_logs(card_id)
    return [
        LogResponse(
            id=l.id, card_id=l.card_id, swimlane_id=l.swimlane_id,
            attempt=l.attempt, process_id=l.process_id,
            prompt=l.prompt, stdout=l.stdout, stderr=l.stderr, exit_code=l.exit_code,
            session_id=l.session_id, started_at=l.started_at,
            finished_at=l.finished_at, created_at=l.created_at,
        ) for l in logs
    ]


@router.get("/logs/cards/summary", response_model=list[CardLogSummary])
async def get_card_log_summary(
    status: str = Query(None, description="筛选状态: completed, blocked, errored"),
    db: AsyncSession = Depends(get_db),
):
    """查询已完成/异常卡片列表及其最新日志摘要"""
    # 子查询: 每张卡片最新的一条日志
    latest_log_subq = (
        select(Log.id)
        .where(Log.card_id == Card.id)
        .order_by(desc(Log.started_at))
        .limit(1)
        .correlate(Card)
        .scalar_subquery()
    )

    conditions = [Card.status.in_(["completed", "blocked", "errored"])]
    if status:
        conditions = [Card.status == status]

    query = (
        select(Card, Kanban.name, Log)
        .join(Kanban, Card.kanban_id == Kanban.id)
        .outerjoin(Log, Log.id == latest_log_subq)
        .where(*conditions)
        .order_by(desc(Card.updated_at))
    )

    result = await db.execute(query)
    rows = result.all()

    summaries = []
    for card, kanban_name, log in rows:
        stdout_preview = ""
        if log and log.stdout:
            stdout_preview = log.stdout.strip()[:200]
        summaries.append(CardLogSummary(
            card_id=card.id,
            card_title=card.title,
            card_status=card.status,
            kanban_id=card.kanban_id,
            kanban_name=kanban_name,
            log_id=log.id if log else None,
            swimlane_id=log.swimlane_id if log else None,
            exit_code=log.exit_code if log else None,
            session_id=log.session_id if log else None,
            started_at=log.started_at if log else None,
            finished_at=log.finished_at if log else None,
            stdout_preview=stdout_preview,
        ))
    return summaries


@router.get("/logs/{log_id}/stdout", response_class=PlainTextResponse)
async def get_log_stdout(log_id: str, db: AsyncSession = Depends(get_db)):
    service = LogService(db)
    log = await service.get_log(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    return log.stdout or ""


@router.get("/logs/{log_id}/stderr", response_class=PlainTextResponse)
async def get_log_stderr(log_id: str, db: AsyncSession = Depends(get_db)):
    service = LogService(db)
    log = await service.get_log(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    return log.stderr or ""
