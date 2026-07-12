from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_tenant_id
from ..models.constraint import PersonConstraint
from ..schemas.common import PersonConstraintCreate, PersonConstraintResponse

router = APIRouter(prefix="/api/constraints", tags=["constraints"])


@router.get("", response_model=list[PersonConstraintResponse])
async def list_constraints(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PersonConstraint).where(PersonConstraint.tenant_id == tenant_id)
    )
    rows = result.scalars().all()
    return [
        PersonConstraintResponse(
            id=r.id, member_id=r.member_id,
            weekly_work_days_min=r.weekly_work_days_min,
            weekly_work_days_max=r.weekly_work_days_max,
            period_work_days_min=r.period_work_days_min,
            period_work_days_max=r.period_work_days_max,
            weekly_work_hours_min=r.weekly_work_hours_min,
            weekly_work_hours_max=r.weekly_work_hours_max,
            period_work_hours_min=r.period_work_hours_min,
            period_work_hours_max=r.period_work_hours_max,
            max_consecutive_work_days=r.max_consecutive_work_days,
            max_consecutive_rest_days=r.max_consecutive_rest_days,
        )
        for r in rows
    ]


@router.get("/{constraint_id}", response_model=PersonConstraintResponse)
async def get_constraint(
    constraint_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PersonConstraint).where(
            PersonConstraint.id == constraint_id,
            PersonConstraint.tenant_id == tenant_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Constraint not found")
    return PersonConstraintResponse(
        id=row.id, member_id=row.member_id,
        weekly_work_days_min=row.weekly_work_days_min,
        weekly_work_days_max=row.weekly_work_days_max,
        period_work_days_min=row.period_work_days_min,
        period_work_days_max=row.period_work_days_max,
        weekly_work_hours_min=row.weekly_work_hours_min,
        weekly_work_hours_max=row.weekly_work_hours_max,
        period_work_hours_min=row.period_work_hours_min,
        period_work_hours_max=row.period_work_hours_max,
        max_consecutive_work_days=row.max_consecutive_work_days,
        max_consecutive_rest_days=row.max_consecutive_rest_days,
    )


@router.post("", response_model=PersonConstraintResponse, status_code=201)
async def create_constraint(
    body: PersonConstraintCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    constraint = PersonConstraint(
        id=str(uuid.uuid4()), tenant_id=tenant_id,
        member_id=body.member_id,
        weekly_work_days_min=body.weekly_work_days_min,
        weekly_work_days_max=body.weekly_work_days_max,
        period_work_days_min=body.period_work_days_min,
        period_work_days_max=body.period_work_days_max,
        weekly_work_hours_min=body.weekly_work_hours_min,
        weekly_work_hours_max=body.weekly_work_hours_max,
        period_work_hours_min=body.period_work_hours_min,
        period_work_hours_max=body.period_work_hours_max,
        max_consecutive_work_days=body.max_consecutive_work_days,
        max_consecutive_rest_days=body.max_consecutive_rest_days,
    )
    db.add(constraint)
    await db.commit()
    return PersonConstraintResponse(
        id=constraint.id, member_id=constraint.member_id,
        weekly_work_days_min=constraint.weekly_work_days_min,
        weekly_work_days_max=constraint.weekly_work_days_max,
        period_work_days_min=constraint.period_work_days_min,
        period_work_days_max=constraint.period_work_days_max,
        weekly_work_hours_min=constraint.weekly_work_hours_min,
        weekly_work_hours_max=constraint.weekly_work_hours_max,
        period_work_hours_min=constraint.period_work_hours_min,
        period_work_hours_max=constraint.period_work_hours_max,
        max_consecutive_work_days=constraint.max_consecutive_work_days,
        max_consecutive_rest_days=constraint.max_consecutive_rest_days,
    )


@router.put("/{constraint_id}", response_model=PersonConstraintResponse)
async def update_constraint(
    constraint_id: str,
    body: PersonConstraintCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PersonConstraint).where(
            PersonConstraint.id == constraint_id,
            PersonConstraint.tenant_id == tenant_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Constraint not found")
    row.member_id = body.member_id
    row.weekly_work_days_min = body.weekly_work_days_min
    row.weekly_work_days_max = body.weekly_work_days_max
    row.period_work_days_min = body.period_work_days_min
    row.period_work_days_max = body.period_work_days_max
    row.weekly_work_hours_min = body.weekly_work_hours_min
    row.weekly_work_hours_max = body.weekly_work_hours_max
    row.period_work_hours_min = body.period_work_hours_min
    row.period_work_hours_max = body.period_work_hours_max
    row.max_consecutive_work_days = body.max_consecutive_work_days
    row.max_consecutive_rest_days = body.max_consecutive_rest_days
    await db.commit()
    return PersonConstraintResponse(
        id=row.id, member_id=row.member_id,
        weekly_work_days_min=row.weekly_work_days_min,
        weekly_work_days_max=row.weekly_work_days_max,
        period_work_days_min=row.period_work_days_min,
        period_work_days_max=row.period_work_days_max,
        weekly_work_hours_min=row.weekly_work_hours_min,
        weekly_work_hours_max=row.weekly_work_hours_max,
        period_work_hours_min=row.period_work_hours_min,
        period_work_hours_max=row.period_work_hours_max,
        max_consecutive_work_days=row.max_consecutive_work_days,
        max_consecutive_rest_days=row.max_consecutive_rest_days,
    )


@router.delete("/{constraint_id}", status_code=204)
async def delete_constraint(
    constraint_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PersonConstraint).where(
            PersonConstraint.id == constraint_id,
            PersonConstraint.tenant_id == tenant_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Constraint not found")
    await db.delete(row)
    await db.commit()
