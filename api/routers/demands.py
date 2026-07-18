from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_tenant_id
from ..models.demand import DailyDemand, PatternDemand
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


class DailyDemandUpdate(BaseModel):
    min_total: int
    max_total: int


@router.put("/{schedule_id}/demands/{demand_id}", response_model=DailyDemandResponse)
async def update_demand(
    schedule_id: str,
    demand_id: str,
    body: DailyDemandUpdate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_schedule(schedule_id, tenant_id, db)
    result = await db.execute(
        select(DailyDemand).where(
            DailyDemand.id == demand_id,
            DailyDemand.schedule_id == schedule_id,
            DailyDemand.tenant_id == tenant_id,
        )
    )
    demand = result.scalar_one_or_none()
    if demand is None:
        raise HTTPException(status_code=404, detail="Demand not found")
    demand.min_total = body.min_total
    demand.max_total = body.max_total
    await db.commit()
    return DailyDemandResponse(
        id=demand.id, schedule_id=demand.schedule_id,
        date=demand.date, min_total=demand.min_total, max_total=demand.max_total,
    )


class DailyDemandWeekdayBatch(BaseModel):
    weekday_settings: dict[int, dict]  # {0: {min_total, max_total}, ..., 6: ...}


@router.post("/{schedule_id}/demands/batch-weekday", response_model=list[DailyDemandResponse])
async def batch_set_demands_by_weekday(
    schedule_id: str,
    body: DailyDemandWeekdayBatch,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
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
        wd = d.weekday()
        setting = body.weekday_settings.get(wd, body.weekday_settings.get(0, {}))
        demand = DailyDemand(
            id=str(uuid.uuid4()), tenant_id=tenant_id,
            schedule_id=schedule_id, date=d,
            min_total=setting.get("min_total", 0),
            max_total=setting.get("max_total", 999),
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


# --- Pattern Demand endpoints ---

class PatternDemandCreate(BaseModel):
    pattern_id: str
    min_count: int = 0


class PatternDemandResponse(PatternDemandCreate):
    id: str
    schedule_id: str
    date: str


class PatternDemandBatch(BaseModel):
    pattern_id: str
    min_count: int = 0


@router.get("/{schedule_id}/pattern-demands")
async def list_pattern_demands(
    schedule_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_schedule(schedule_id, tenant_id, db)
    result = await db.execute(
        select(PatternDemand).where(
            PatternDemand.schedule_id == schedule_id,
            PatternDemand.tenant_id == tenant_id,
        )
    )
    return [
        {"id": pd.id, "schedule_id": pd.schedule_id, "date": str(pd.date), "pattern_id": pd.pattern_id, "min_count": pd.min_count}
        for pd in result.scalars().all()
    ]


@router.post("/{schedule_id}/pattern-demands/batch")
async def batch_set_pattern_demands(
    schedule_id: str,
    body: PatternDemandBatch,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    schedule = await _get_schedule(schedule_id, tenant_id, db)
    await db.execute(
        delete(PatternDemand).where(
            PatternDemand.schedule_id == schedule_id,
            PatternDemand.tenant_id == tenant_id,
            PatternDemand.pattern_id == body.pattern_id,
        )
    )
    items = []
    for i in range(schedule.num_days):
        d = schedule.start_date + timedelta(days=i)
        pd = PatternDemand(
            id=str(uuid.uuid4()), tenant_id=tenant_id,
            schedule_id=schedule_id, date=d,
            pattern_id=body.pattern_id, min_count=body.min_count,
        )
        db.add(pd)
        items.append(pd)
    await db.commit()
    return [
        {"id": p.id, "schedule_id": p.schedule_id, "date": str(p.date), "pattern_id": p.pattern_id, "min_count": p.min_count}
        for p in items
    ]


class PatternDemandWeekdayBatch(BaseModel):
    pattern_id: str
    weekday_settings: dict[int, dict]  # {0: {min_count: N}, ..., 6: ...}


@router.post("/{schedule_id}/pattern-demands/batch-weekday")
async def batch_set_pattern_demands_by_weekday(
    schedule_id: str,
    body: PatternDemandWeekdayBatch,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    schedule = await _get_schedule(schedule_id, tenant_id, db)
    await db.execute(
        delete(PatternDemand).where(
            PatternDemand.schedule_id == schedule_id,
            PatternDemand.tenant_id == tenant_id,
            PatternDemand.pattern_id == body.pattern_id,
        )
    )
    items = []
    for i in range(schedule.num_days):
        d = schedule.start_date + timedelta(days=i)
        wd = d.weekday()
        setting = body.weekday_settings.get(wd, body.weekday_settings.get(0, {}))
        mc = setting.get("min_count", 0)
        if mc <= 0:
            continue
        pd = PatternDemand(
            id=str(uuid.uuid4()), tenant_id=tenant_id,
            schedule_id=schedule_id, date=d,
            pattern_id=body.pattern_id, min_count=mc,
        )
        db.add(pd)
        items.append(pd)
    await db.commit()
    return [
        {"id": p.id, "schedule_id": p.schedule_id, "date": str(p.date), "pattern_id": p.pattern_id, "min_count": p.min_count}
        for p in items
    ]


class PatternDemandUpdate(BaseModel):
    min_count: int


@router.put("/{schedule_id}/pattern-demands/{demand_id}")
async def update_pattern_demand(
    schedule_id: str,
    demand_id: str,
    body: PatternDemandUpdate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_schedule(schedule_id, tenant_id, db)
    result = await db.execute(
        select(PatternDemand).where(
            PatternDemand.id == demand_id,
            PatternDemand.schedule_id == schedule_id,
            PatternDemand.tenant_id == tenant_id,
        )
    )
    pd = result.scalar_one_or_none()
    if pd is None:
        raise HTTPException(status_code=404, detail="Pattern demand not found")
    pd.min_count = body.min_count
    await db.commit()
    return {"id": pd.id, "schedule_id": pd.schedule_id, "date": str(pd.date), "pattern_id": pd.pattern_id, "min_count": pd.min_count}


@router.delete("/{schedule_id}/pattern-demands", status_code=204)
async def clear_pattern_demands(
    schedule_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_schedule(schedule_id, tenant_id, db)
    await db.execute(
        delete(PatternDemand).where(
            PatternDemand.schedule_id == schedule_id,
            PatternDemand.tenant_id == tenant_id,
        )
    )
    await db.commit()
