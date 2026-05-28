import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


class Log(Base):
    __tablename__ = "logs"

    id = Column(String, primary_key=True, default=_uuid)
    card_id = Column(String, ForeignKey("cards.id", ondelete="CASCADE"), nullable=False)
    swimlane_id = Column(String, ForeignKey("swimlanes.id"), nullable=False)
    attempt = Column(Integer, nullable=False, default=1)
    process_id = Column(Integer, nullable=True)
    stdout = Column(Text, default="")
    stderr = Column(Text, default="")
    exit_code = Column(Integer, nullable=True)
    session_id = Column(String, nullable=True)
    started_at = Column(String, nullable=True)
    finished_at = Column(String, nullable=True)
    created_at = Column(String, nullable=False, default=_utcnow)

    card = relationship("Card", back_populates="logs")
