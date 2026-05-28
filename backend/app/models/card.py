import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


class Card(Base):
    __tablename__ = "cards"

    id = Column(String, primary_key=True, default=_uuid)
    kanban_id = Column(String, ForeignKey("kanbans.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    model = Column(String, nullable=False)
    current_swimlane_id = Column(String, ForeignKey("swimlanes.id"), nullable=True)
    status = Column(String, nullable=False, default="pending")
    # pending | running | waiting_approval | approved | rejected | completed | blocked
    session_id = Column(String, nullable=True)
    rejection_note = Column(Text, nullable=True)
    created_at = Column(String, nullable=False, default=_utcnow)
    updated_at = Column(String, nullable=False, default=_utcnow, onupdate=_utcnow)

    current_swimlane = relationship("Swimlane", back_populates="cards", foreign_keys=[current_swimlane_id])
    logs = relationship("Log", back_populates="card", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="card", cascade="all, delete-orphan")
