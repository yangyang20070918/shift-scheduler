from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_tenant_id
from ..models.demand import DailyDemand
from ..models.schedule import Schedule
from ..schemas.common import DailyDemandBatch, DailyDemandCreate, DailyDemandResponse

router = APIRouter(prefix="/api/schedules", tags=["demands"])


async def _get_schedule(schedule_id: str, tenant_id: str, db: AsyncSession) -> Schedule:
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id, Schedule.tenant_id == tenant_id)
    )
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.get("/{schedule_id}/demands", response_model=list[DailyDemandResponse])
async def list_demands(
    schedule_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_schedule(schedule_id, tenant_id, db)
    result = await db.execute(
        select(DailyDemand).where(
            DailyDemand.schedule_id == schedule_id,
            DailyDemand.tenant_id == tenant_id,
        )
    )
    demands = result.scalars().all()
    return [
        DailyDemandResponse(
            id=d.id, schedule_id=d.schedule_id,
            date=d.date, min_total=d.min_total, max_total=d.max_total,
        )
        for d in demands
    ]


@router.post("/{schedule_id}/demands", response_model=DailyDemandResponse, status_code=201)
async def create_demand(
    schedule_id: str,
    body: DailyDemandCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    schedule = await _get_schedule(schedule_id, tenant_id, db)
    demand = DailyDemand(
        id=str(uuid.uuid4()), tenant_id=tenant_id,
        schedule_id=schedule_id, date=body.date,
        min_total=body.min_total, max_total=body.max_total,
    )
    db.add(demand)
    await db.commit()
    return DailyDemandResponse(
        id=demand.id, schedule_id=demand.schedule_id,
        date=demand.date, min_total=demand.min_total, max_total=demand.max_total,
    )


@router.post("/{schedule_id}/demands/batch", response_model=list[DailyDemandResponse])
async def batch_set_demands(
    schedule_id: str,
    body: DailyDemandBatch,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Set uniform daily demands for all dates in the schedule period."""
    schedule = await _get_schedule(schedule_id, tenant_id, db)
    await db.execute(
        delete(DailyDemand).where(
            DailyDemand.schedule_id == schedule_id,
            DailyDemand.tenant_id == tenant_id,
        )
    )
    demands = []
    for i in range(schedule.num_days):
        d = schedule.start_date + timedelta(days=i)
        demand = DailyDemand(
            id=str(uuid.uuid4()), tenant_id=tenant_id,
            schedule_id=schedule_id, date=d,
            min_total=body.min_total, max_total=body.max_total,
        )
        db.add(demand)
        demands.append(demand)
    await db.commit()
    return [
        DailyDemandResponse(
            id=dm.id, schedule_id=dm.schedule_id,
            date=dm.date, min_total=dm.min_total, max_total=dm.max_total,
        )
        for dm in demands
    ]


@router.delete("/{schedule_id}/demands", status_code=204)
async def clear_demands(
    schedule_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_schedule(schedule_id, tenant_id, db)
    await db.execute(
        delete(DailyDemand).where(
            DailyDemand.schedule_id == schedule_id,
            DailyDemand.tenant_id == tenant_id,
        )
    )
    await db.commit()
