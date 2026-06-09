from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.kanban_service import KanbanService, SwimlaneService
from app.schemas.kanban import (
    KanbanCreate, KanbanUpdate, KanbanResponse, SwimlaneBrief,
    SwimlaneCreate, SwimlaneUpdate, SwimlaneResponse, SwimlaneOrderRequest,
    KanbanImportData, KanbanImportResult,
)

router = APIRouter(prefix="/api")


@router.get("/kanbans", response_model=list[KanbanResponse])
async def list_kanbans(db: AsyncSession = Depends(get_db)):
    service = KanbanService(db)
    swimlane_service = SwimlaneService(db)
    kanbans = await service.list()
    result = []
    for k in kanbans:
        swimlanes = await swimlane_service.get_kanban_swimlanes(k.id)
        briefs = []
        for s in swimlanes:
            card_count = await service.get_card_count(k.id)
            briefs.append(SwimlaneBrief(
                id=s.id, name=s.name, sort_order=s.sort_order,
                flow_mode=s.flow_mode, local_path=s.local_path, card_count=0,
                wait_for_reply=s.wait_for_reply,
                local_path_permission=s.local_path_permission,
                allowed_paths=s.allowed_paths,
                swimlane_type=s.swimlane_type,
            ))
        result.append(KanbanResponse(
            id=k.id, name=k.name, description=k.description or "",
            created_at=k.created_at, updated_at=k.updated_at,
            swimlanes=briefs,
        ))
    return result


@router.post("/kanbans", response_model=KanbanResponse, status_code=201)
async def create_kanban(data: KanbanCreate, db: AsyncSession = Depends(get_db)):
    if not data.name.strip():
        raise HTTPException(status_code=422, detail="看板名称不能为空")
    service = KanbanService(db)
    kanban = await service.create(data.name.strip(), data.description)
    return KanbanResponse(
        id=kanban.id, name=kanban.name, description=kanban.description or "",
        created_at=kanban.created_at, updated_at=kanban.updated_at,
    )


@router.get("/kanbans/{kanban_id}", response_model=KanbanResponse)
async def get_kanban(kanban_id: str, db: AsyncSession = Depends(get_db)):
    service = KanbanService(db)
    swimlane_service = SwimlaneService(db)
    kanban = await service.get(kanban_id)
    if not kanban:
        raise HTTPException(status_code=404, detail="看板不存在")
    swimlanes = await swimlane_service.get_kanban_swimlanes(kanban_id)
    briefs = []
    for s in swimlanes:
        briefs.append(SwimlaneBrief(
            id=s.id, name=s.name, sort_order=s.sort_order,
            prompt=s.prompt, skill=s.skill, tools=s.tools,
            swimlane_type=s.swimlane_type,
            flow_mode=s.flow_mode, local_path=s.local_path, card_count=0,
            wait_for_reply=s.wait_for_reply,
            local_path_permission=s.local_path_permission,
            allowed_paths=s.allowed_paths,
        ))
    return KanbanResponse(
        id=kanban.id, name=kanban.name, description=kanban.description or "",
        created_at=kanban.created_at, updated_at=kanban.updated_at,
        swimlanes=briefs,
    )


@router.put("/kanbans/{kanban_id}", response_model=KanbanResponse)
async def update_kanban(kanban_id: str, data: KanbanUpdate,
                        db: AsyncSession = Depends(get_db)):
    service = KanbanService(db)
    kanban = await service.update(kanban_id, name=data.name, description=data.description)
    if not kanban:
        raise HTTPException(status_code=404, detail="看板不存在")
    return KanbanResponse(
        id=kanban.id, name=kanban.name, description=kanban.description or "",
        created_at=kanban.created_at, updated_at=kanban.updated_at,
    )


@router.delete("/kanbans/{kanban_id}")
async def delete_kanban(kanban_id: str, db: AsyncSession = Depends(get_db)):
    service = KanbanService(db)
    success = await service.delete(kanban_id)
    if not success:
        raise HTTPException(status_code=404, detail="看板不存在")
    return {"message": "看板已删除"}


# === 泳道路由 ===

@router.post("/kanbans/{kanban_id}/swimlanes", response_model=SwimlaneResponse, status_code=201)
async def add_swimlane(kanban_id: str, data: SwimlaneCreate,
                       db: AsyncSession = Depends(get_db)):
    service = SwimlaneService(db)
    kanban_service = KanbanService(db)
    if not await kanban_service.get(kanban_id):
        raise HTTPException(status_code=404, detail="看板不存在")
    s = await service.add_swimlane(
        kanban_id, data.name, data.prompt, data.skill, data.tools,
        data.swimlane_type, data.flow_mode,
        local_path=data.local_path, wait_for_reply=data.wait_for_reply,
        local_path_permission=data.local_path_permission, allowed_paths=data.allowed_paths,
    )
    return SwimlaneResponse(
        id=s.id, kanban_id=s.kanban_id, name=s.name, sort_order=s.sort_order,
        prompt=s.prompt, skill=s.skill, tools=s.tools,
        swimlane_type=s.swimlane_type, flow_mode=s.flow_mode,
        local_path=s.local_path, wait_for_reply=s.wait_for_reply,
        local_path_permission=s.local_path_permission, allowed_paths=s.allowed_paths,
        created_at=s.created_at, updated_at=s.updated_at,
    )


@router.put("/swimlanes/{swimlane_id}", response_model=SwimlaneResponse)
async def update_swimlane(swimlane_id: str, data: SwimlaneUpdate,
                          db: AsyncSession = Depends(get_db)):
    service = SwimlaneService(db)
    update_data = data.model_dump(exclude_none=True)
    s = await service.update(swimlane_id, **update_data)
    if not s:
        raise HTTPException(status_code=404, detail="泳道不存在")
    return SwimlaneResponse(
        id=s.id, kanban_id=s.kanban_id, name=s.name, sort_order=s.sort_order,
        prompt=s.prompt, skill=s.skill, tools=s.tools,
        swimlane_type=s.swimlane_type, flow_mode=s.flow_mode,
        local_path=s.local_path, wait_for_reply=s.wait_for_reply,
        local_path_permission=s.local_path_permission, allowed_paths=s.allowed_paths,
        created_at=s.created_at, updated_at=s.updated_at,
    )


@router.delete("/swimlanes/{swimlane_id}")
async def delete_swimlane(swimlane_id: str, db: AsyncSession = Depends(get_db)):
    service = SwimlaneService(db)
    success, msg = await service.delete(swimlane_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": "泳道已删除"}


@router.put("/kanbans/{kanban_id}/swimlanes/order")
async def reorder_swimlanes(kanban_id: str, data: SwimlaneOrderRequest,
                             db: AsyncSession = Depends(get_db)):
    service = SwimlaneService(db)
    await service.reorder(kanban_id, data.swimlane_ids)
    return {"message": "泳道顺序已更新"}


# === 导出/导入路由 ===

@router.get("/kanbans/{kanban_id}/export")
async def export_kanban(kanban_id: str, db: AsyncSession = Depends(get_db)):
    """导出看板配置为 JSON"""
    service = KanbanService(db)
    data = await service.export_config(kanban_id)
    if not data:
        raise HTTPException(status_code=404, detail="看板不存在")
    return JSONResponse(
        content=data,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="kanban-{kanban_id[:8]}.json"',
        },
    )


@router.post("/kanbans/import", response_model=KanbanImportResult, status_code=201)
async def import_kanban(data: KanbanImportData, db: AsyncSession = Depends(get_db)):
    """从 JSON 配置导入看板"""
    service = KanbanService(db)
    try:
        kanban = await service.import_config(data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    swimlane_service = SwimlaneService(db)
    swimlanes = await swimlane_service.get_kanban_swimlanes(kanban.id)

    return KanbanImportResult(
        id=kanban.id,
        name=kanban.name,
        description=kanban.description or "",
        swimlane_count=len(swimlanes),
    )
