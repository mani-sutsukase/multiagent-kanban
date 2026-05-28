from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.setting import Setting
from app.schemas.setting import SettingUpdate, SettingResponse

router = APIRouter(prefix="/api")


@router.get("/settings", response_model=list[SettingResponse])
async def list_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Setting))
    settings = result.scalars().all()
    return [
        SettingResponse(key=s.key, value=s.value) for s in settings
    ]


@router.get("/settings/{key}", response_model=SettingResponse)
async def get_setting(key: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="设置不存在")
    return SettingResponse(key=setting.key, value=setting.value)


@router.put("/settings/{key}", response_model=SettingResponse)
async def update_setting(key: str, data: SettingUpdate,
                          db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = data.value
    else:
        setting = Setting(key=key, value=data.value)
        db.add(setting)
    await db.commit()
    await db.refresh(setting)
    return SettingResponse(key=setting.key, value=setting.value)
