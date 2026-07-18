from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user, get_tenant_id
from ..models.pattern import ShiftPattern
from ..models.user import User
from ..schemas.common import PatternCreate, PatternResponse
from ..services.audit import record_audit

router = APIRouter(prefix="/api/patterns", tags=["patterns"])

_API_TYPE_MAP = {"NORMAL": "work", "REST": "rest", "LEAVE": "rest", "HOLIDAY": "rest", "TRAVEL": "travel"}
_IMPORT_TYPE_MAP = {"work": "NORMAL", "rest": "REST", "travel": "TRAVEL"}


@router.get("", response_model=list[PatternResponse])
async def list_patterns(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ShiftPattern).where(ShiftPattern.tenant_id == tenant_id))
    patterns = result.scalars().all()
    return [
        PatternResponse(
            id=p.id, name=p.name, type=_API_TYPE_MAP.get(p.type, p.type),
            start_time=p.start_time, end_time=p.end_time,
            break_hours=p.break_hours, work_hours=p.work_hours,
            is_companion=p.is_companion, color_code=p.color_code,
        )
        for p in patterns
    ]


@router.post("", response_model=PatternResponse, status_code=201)
async def create_pattern(
    body: PatternCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pattern = ShiftPattern(
        id=str(uuid.uuid4()), tenant_id=user.tenant_id,
        name=body.name, type=body.type,
        start_time=body.start_time, end_time=body.end_time,
        break_hours=body.break_hours, work_hours=body.work_hours,
        is_companion=body.is_companion, color_code=body.color_code,
    )
    db.add(pattern)
    await db.commit()
    await record_audit(db, tenant_id=user.tenant_id, action="CREATE", resource_type="pattern",
                       user_id=user.id, user_email=user.email, resource_id=pattern.id,
                       detail={"name": body.name, "type": body.type}, request=request)
    return PatternResponse(
        id=pattern.id, name=pattern.name, type=_API_TYPE_MAP.get(pattern.type, pattern.type),
        start_time=pattern.start_time, end_time=pattern.end_time,
        break_hours=pattern.break_hours, work_hours=pattern.work_hours,
        is_companion=pattern.is_companion, color_code=pattern.color_code,
    )


@router.get("/export/excel")
async def export_patterns_excel(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(select(ShiftPattern).where(ShiftPattern.tenant_id == tenant_id))
    patterns = [
        {
            "name": p.name,
            "type": _API_TYPE_MAP.get(p.type, p.type),
            "start_time": p.start_time,
            "end_time": p.end_time,
            "break_hours": p.break_hours,
            "work_hours": p.work_hours,
            "color_code": p.color_code,
        }
        for p in q.scalars().all()
    ]
    from ..services.export_excel import generate_pattern_excel
    buf = generate_pattern_excel(patterns)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="patterns.xlsx"'},
    )


@router.post("/import/preview")
async def preview_pattern_import(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    from ..services.import_excel import parse_pattern_excel
    parsed = parse_pattern_excel(content)

    q = await db.execute(select(ShiftPattern).where(ShiftPattern.tenant_id == tenant_id))
    existing = {p.name: p for p in q.scalars().all()}

    preview = {"patterns": [], "warnings": []}
    for p in parsed:
        name = p.get("name", "")
        status = "update" if name in existing else "new"
        preview["patterns"].append({**p, "status": status})
        ptype = p.get("type", "work")
        if ptype == "work" and (not p.get("start_time") or not p.get("end_time")):
            preview["warnings"].append(f"勤務パターン「{name}」の開始/終了時刻が未設定です")
        if ptype != "rest" and not p.get("work_hours"):
            preview["warnings"].append(f"パターン「{name}」の実労働時間が未設定です")

    return preview


@router.post("/import/execute")
async def execute_pattern_import(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    from ..services.import_excel import parse_pattern_excel
    parsed = parse_pattern_excel(content)

    q = await db.execute(select(ShiftPattern).where(ShiftPattern.tenant_id == tenant_id))
    existing = {p.name: p for p in q.scalars().all()}

    created = 0
    updated = 0
    for p in parsed:
        name = p.get("name", "")
        ptype = _IMPORT_TYPE_MAP.get(p.get("type", "work"), "NORMAL")
        if name in existing:
            pat = existing[name]
            pat.type = ptype
            pat.start_time = p.get("start_time", pat.start_time)
            pat.end_time = p.get("end_time", pat.end_time)
            pat.break_hours = p.get("break_hours", pat.break_hours)
            pat.work_hours = p.get("work_hours", pat.work_hours)
            if p.get("color_code"):
                pat.color_code = p["color_code"]
            updated += 1
        else:
            pat = ShiftPattern(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name=name,
                type=ptype,
                start_time=p.get("start_time", "09:00"),
                end_time=p.get("end_time", "17:00"),
                break_hours=p.get("break_hours", 0),
                work_hours=p.get("work_hours", 8),
                color_code=p.get("color_code", "#808080"),
            )
            db.add(pat)
            created += 1

    await db.commit()
    return {"created": created, "updated": updated}


@router.put("/{pattern_id}", response_model=PatternResponse)
async def update_pattern(
    pattern_id: str,
    body: PatternCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ShiftPattern).where(ShiftPattern.id == pattern_id, ShiftPattern.tenant_id == user.tenant_id))
    pattern = result.scalar_one_or_none()
    if pattern is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    old_name = pattern.name
    pattern.name = body.name
    pattern.type = body.type
    pattern.start_time = body.start_time
    pattern.end_time = body.end_time
    pattern.break_hours = body.break_hours
    pattern.work_hours = body.work_hours
    pattern.is_companion = body.is_companion
    pattern.color_code = body.color_code
    await db.commit()
    await record_audit(db, tenant_id=user.tenant_id, action="UPDATE", resource_type="pattern",
                       user_id=user.id, user_email=user.email, resource_id=pattern_id,
                       detail={"old_name": old_name, "new_name": body.name}, request=request)
    return PatternResponse(
        id=pattern.id, name=pattern.name, type=_API_TYPE_MAP.get(pattern.type, pattern.type),
        start_time=pattern.start_time, end_time=pattern.end_time,
        break_hours=pattern.break_hours, work_hours=pattern.work_hours,
        is_companion=pattern.is_companion, color_code=pattern.color_code,
    )


@router.delete("/{pattern_id}", status_code=204)
async def delete_pattern(
    pattern_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ShiftPattern).where(ShiftPattern.id == pattern_id, ShiftPattern.tenant_id == user.tenant_id))
    pattern = result.scalar_one_or_none()
    if pattern is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    name = pattern.name
    await db.delete(pattern)
    await db.commit()
    await record_audit(db, tenant_id=user.tenant_id, action="DELETE", resource_type="pattern",
                       user_id=user.id, user_email=user.email, resource_id=pattern_id,
                       detail={"name": name}, request=request)
