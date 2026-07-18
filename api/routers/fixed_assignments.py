from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_tenant_id
from ..models.schedule import FixedAssignment, Schedule
from ..schemas.common import FixedAssignmentCreate, FixedAssignmentResponse

router = APIRouter(prefix="/api/schedules", tags=["fixed-assignments"])


async def _get_schedule(schedule_id: str, tenant_id: str, db: AsyncSession) -> Schedule:
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id, Schedule.tenant_id == tenant_id)
    )
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.get("/{schedule_id}/fixed-assignments", response_model=list[FixedAssignmentResponse])
async def list_fixed_assignments(
    schedule_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_schedule(schedule_id, tenant_id, db)
    result = await db.execute(
        select(FixedAssignment).where(
            FixedAssignment.schedule_id == schedule_id,
            FixedAssignment.tenant_id == tenant_id,
        )
    )
    rows = result.scalars().all()
    return [
        FixedAssignmentResponse(
            id=r.id, schedule_id=r.schedule_id,
            member_id=r.member_id, date=r.date,
            type=r.type, pattern_id=r.pattern_id,
        )
        for r in rows
    ]


@router.post("/{schedule_id}/fixed-assignments", response_model=FixedAssignmentResponse, status_code=201)
async def create_fixed_assignment(
    schedule_id: str,
    body: FixedAssignmentCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_schedule(schedule_id, tenant_id, db)
    fa = FixedAssignment(
        id=str(uuid.uuid4()), tenant_id=tenant_id,
        schedule_id=schedule_id,
        member_id=body.member_id, date=body.date,
        type=body.type, pattern_id=body.pattern_id,
    )
    db.add(fa)
    await db.commit()
    return FixedAssignmentResponse(
        id=fa.id, schedule_id=fa.schedule_id,
        member_id=fa.member_id, date=fa.date,
        type=fa.type, pattern_id=fa.pattern_id,
    )


@router.put("/{schedule_id}/fixed-assignments/{assignment_id}", response_model=FixedAssignmentResponse)
async def update_fixed_assignment(
    schedule_id: str,
    assignment_id: str,
    body: FixedAssignmentCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_schedule(schedule_id, tenant_id, db)
    result = await db.execute(
        select(FixedAssignment).where(
            FixedAssignment.id == assignment_id,
            FixedAssignment.schedule_id == schedule_id,
            FixedAssignment.tenant_id == tenant_id,
        )
    )
    fa = result.scalar_one_or_none()
    if fa is None:
        raise HTTPException(status_code=404, detail="Fixed assignment not found")
    fa.member_id = body.member_id
    fa.date = body.date
    fa.type = body.type
    fa.pattern_id = body.pattern_id
    await db.commit()
    return FixedAssignmentResponse(
        id=fa.id, schedule_id=fa.schedule_id,
        member_id=fa.member_id, date=fa.date,
        type=fa.type, pattern_id=fa.pattern_id,
    )


@router.delete("/{schedule_id}/fixed-assignments/{assignment_id}", status_code=204)
async def delete_fixed_assignment(
    schedule_id: str,
    assignment_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_schedule(schedule_id, tenant_id, db)
    result = await db.execute(
        select(FixedAssignment).where(
            FixedAssignment.id == assignment_id,
            FixedAssignment.schedule_id == schedule_id,
            FixedAssignment.tenant_id == tenant_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Fixed assignment not found")
    await db.delete(row)
    await db.commit()


@router.delete("/{schedule_id}/fixed-assignments", status_code=204)
async def clear_fixed_assignments(
    schedule_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_schedule(schedule_id, tenant_id, db)
    await db.execute(
        delete(FixedAssignment).where(
            FixedAssignment.schedule_id == schedule_id,
            FixedAssignment.tenant_id == tenant_id,
        )
    )
    await db.commit()
