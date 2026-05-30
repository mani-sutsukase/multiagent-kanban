import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


class Kanban(Base):
    __tablename__ = "kanbans"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    created_at = Column(String, nullable=False, default=_utcnow)
    updated_at = Column(String, nullable=False, default=_utcnow, onupdate=_utcnow)

    swimlanes = relationship("Swimlane", back_populates="kanban", cascade="all, delete-orphan",
                             order_by="Swimlane.sort_order")


class Swimlane(Base):
    __tablename__ = "swimlanes"

    id = Column(String, primary_key=True, default=_uuid)
    kanban_id = Column(String, ForeignKey("kanbans.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    prompt = Column(Text, nullable=False, default="")
    skill = Column(String, nullable=True)
    tools = Column(String, default="[]")  # JSON array
    flow_mode = Column(String, nullable=False, default="auto")  # auto | pre_approval | post_approval
    wait_for_reply = Column(String, nullable=False, default="0")  # "0" 不等待回复 "1" 执行后等待用户回复
    local_path = Column(String, nullable=True)  # 本地工作目录，用于启动 Claude 时的 cwd
    local_path_permission = Column(String, nullable=False, default="read_write")  # read_only / read_write
    allowed_paths = Column(Text, nullable=False, default="[]")  # JSON: [{"path":"...","permission":"read_only"|"read_write"}]
    created_at = Column(String, nullable=False, default=_utcnow)
    updated_at = Column(String, nullable=False, default=_utcnow, onupdate=_utcnow)

    kanban = relationship("Kanban", back_populates="swimlanes")
    cards = relationship("Card", back_populates="current_swimlane", foreign_keys="Card.current_swimlane_id")
