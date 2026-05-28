from sqlalchemy import Column, String

from app.database import Base


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(128), primary_key=True)
    value = Column(String(1024), nullable=False, default="")
