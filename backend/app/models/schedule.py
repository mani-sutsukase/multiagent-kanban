import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    cron_expr = Column(String, nullable=False)
    enabled = Column(Integer, nullable=False, default=1)
    card_title = Column(String, nullable=False)
    card_content = Column(Text, nullable=False)
    card_model = Column(String, nullable=False)
    target_kanban_id = Column(String, ForeignKey("kanbans.id"), nullable=False)
    target_swimlane_id = Column(String, ForeignKey("swimlanes.id"), nullable=False)
    created_at = Column(String, nullable=False, default=_utcnow)
    updated_at = Column(String, nullable=False, default=_utcnow, onupdate=_utcnow)

    logs = relationship("ScheduleLog", back_populates="schedule", cascade="all, delete-orphan")


class ScheduleLog(Base):
    __tablename__ = "schedule_logs"

    id = Column(String, primary_key=True, default=_uuid)
    schedule_id = Column(String, ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False)
    triggered_at = Column(String, nullable=False)
    created_card_id = Column(String, ForeignKey("cards.id"), nullable=True)
    status = Column(String, nullable=False)  # 'success' | 'failed'
    error_message = Column(Text, nullable=True)
    created_at = Column(String, nullable=False, default=_utcnow)

    schedule = relationship("Schedule", back_populates="logs")
