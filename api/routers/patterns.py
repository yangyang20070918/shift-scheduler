from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_tenant_id
from ..models.pattern import ShiftPattern
from ..schemas.common import PatternCreate, PatternResponse

router = APIRouter(prefix="/api/patterns", tags=["patterns"])


@router.get("", response_model=list[PatternResponse])
async def list_patterns(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ShiftPattern).where(ShiftPattern.tenant_id == tenant_id))
    patterns = result.scalars().all()
    return [
        PatternResponse(
            id=p.id, name=p.name, type=p.type,
            start_time=p.start_time, end_time=p.end_time,
            break_hours=p.break_hours, work_hours=p.work_hours,
            is_companion=p.is_companion, color_code=p.color_code,
        )
        for p in patterns
    ]


@router.post("", response_model=PatternResponse, status_code=201)
async def create_pattern(
    body: PatternCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    pattern = ShiftPattern(
        id=str(uuid.uuid4()), tenant_id=tenant_id,
        name=body.name, type=body.type,
        start_time=body.start_time, end_time=body.end_time,
        break_hours=body.break_hours, work_hours=body.work_hours,
        is_companion=body.is_companion, color_code=body.color_code,
    )
    db.add(pattern)
    await db.commit()
    return PatternResponse(
        id=pattern.id, name=pattern.name, type=pattern.type,
        start_time=pattern.start_time, end_time=pattern.end_time,
        break_hours=pattern.break_hours, work_hours=pattern.work_hours,
        is_companion=pattern.is_companion, color_code=pattern.color_code,
    )


@router.delete("/{pattern_id}", status_code=204)
async def delete_pattern(
    pattern_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ShiftPattern).where(ShiftPattern.id == pattern_id, ShiftPattern.tenant_id == tenant_id))
    pattern = result.scalar_one_or_none()
    if pattern is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    await db.delete(pattern)
    await db.commit()
