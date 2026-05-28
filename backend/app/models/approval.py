import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String, primary_key=True, default=_uuid)
    card_id = Column(String, ForeignKey("cards.id", ondelete="CASCADE"), nullable=False)
    swimlane_id = Column(String, ForeignKey("swimlanes.id"), nullable=False)
    action = Column(String, nullable=False)  # 'approved' | 'rejected'
    note = Column(Text, nullable=True)
    created_at = Column(String, nullable=False, default=_utcnow)

    card = relationship("Card", back_populates="approvals")
