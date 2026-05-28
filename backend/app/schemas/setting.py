from pydantic import BaseModel
from typing import Optional


class SettingUpdate(BaseModel):
    value: str


class SettingResponse(BaseModel):
    key: str
    value: str

    class Config:
        from_attributes = True
