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
    # pending | running | waiting_approval | approved | rejected | waiting_for_reply | completed | blocked | errored
    session_id = Column(String, nullable=True)
    rejection_note = Column(Text, nullable=True)
    result = Column(Text, nullable=True)  # 执行结果：成功描述或失败原因
    last_prompt = Column(Text, nullable=True)  # 最近一次发送给 claude 的提示词
    last_output = Column(Text, nullable=True)  # 最近一次 claude 输出的内容
    user_reply = Column(Text, nullable=True)   # 用户对 claude 的回复
    user_reply_question = Column(Text, nullable=True)  # Claude 提出的问题（JSON 标记解析后存入）
    local_path = Column(String, nullable=True)           # 卡片级工作目录
    local_path_permission = Column(String, nullable=False, default="read_write")  # read_only / read_write
    allowed_paths = Column(Text, nullable=False, default="[]")  # JSON: [{"path":"...","permission":"read_only"|"read_write"}]
    dangerously_skip_permissions = Column(String, nullable=False, default="0")  # "0"=关闭 "1"=启用（跳过所有路径限制）
    created_at = Column(String, nullable=False, default=_utcnow)
    updated_at = Column(String, nullable=False, default=_utcnow, onupdate=_utcnow)

    current_swimlane = relationship("Swimlane", back_populates="cards", foreign_keys=[current_swimlane_id])
    logs = relationship("Log", back_populates="card", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="card", cascade="all, delete-orphan")
