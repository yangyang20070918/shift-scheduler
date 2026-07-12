from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_tenant_id
from ..models.group import Group, GroupMember
from ..models.demand import GroupDemand
from ..models.schedule import Schedule
from ..schemas.common import GroupCreate, GroupResponse, GroupDemandCreate, GroupDemandResponse

router = APIRouter(prefix="/api", tags=["groups"])


@router.get("/groups", response_model=list[GroupResponse])
async def list_groups(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Group).where(Group.tenant_id == tenant_id))
    groups = result.scalars().all()
    out = []
    for g in groups:
        mr = await db.execute(select(GroupMember.member_id).where(GroupMember.group_id == g.id))
        member_ids = [row[0] for row in mr.fetchall()]
        out.append(GroupResponse(id=g.id, name=g.name, member_ids=member_ids))
    return out


@router.post("/groups", response_model=GroupResponse, status_code=201)
async def create_group(
    body: GroupCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    group = Group(id=str(uuid.uuid4()), tenant_id=tenant_id, name=body.name)
    db.add(group)
    for mid in body.member_ids:
        db.add(GroupMember(id=str(uuid.uuid4()), tenant_id=tenant_id, group_id=group.id, member_id=mid))
    await db.commit()
    return GroupResponse(id=group.id, name=group.name, member_ids=body.member_ids)


@router.put("/groups/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: str,
    body: GroupCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Group).where(Group.id == group_id, Group.tenant_id == tenant_id))
    group = result.scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    group.name = body.name
    await db.execute(delete(GroupMember).where(GroupMember.group_id == group_id))
    for mid in body.member_ids:
        db.add(GroupMember(id=str(uuid.uuid4()), tenant_id=tenant_id, group_id=group_id, member_id=mid))
    await db.commit()
    return GroupResponse(id=group.id, name=group.name, member_ids=body.member_ids)


@router.delete("/groups/{group_id}", status_code=204)
async def delete_group(
    group_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Group).where(Group.id == group_id, Group.tenant_id == tenant_id))
    group = result.scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    await db.execute(delete(GroupMember).where(GroupMember.group_id == group_id))
    await db.delete(group)
    await db.commit()


async def _get_schedule(schedule_id: str, tenant_id: str, db: AsyncSession) -> Schedule:
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id, Schedule.tenant_id == tenant_id)
    )
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.get("/schedules/{schedule_id}/group-demands", response_model=list[GroupDemandResponse])
async def list_group_demands(
    schedule_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_schedule(schedule_id, tenant_id, db)
    result = await db.execute(select(GroupDemand).where(
        GroupDemand.schedule_id == schedule_id,
        GroupDemand.tenant_id == tenant_id,
    ))
    demands = result.scalars().all()
    return [
        GroupDemandResponse(
            id=d.id, schedule_id=d.schedule_id,
            date=d.date, group_id=d.group_id,
            pattern_id=d.pattern_id, min_count=d.min_count,
        )
        for d in demands
    ]


@router.post("/schedules/{schedule_id}/group-demands", response_model=GroupDemandResponse, status_code=201)
async def create_group_demand(
    schedule_id: str,
    body: GroupDemandCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_schedule(schedule_id, tenant_id, db)
    demand = GroupDemand(
        id=str(uuid.uuid4()), tenant_id=tenant_id,
        schedule_id=schedule_id, date=body.date,
        group_id=body.group_id, pattern_id=body.pattern_id,
        min_count=body.min_count,
    )
    db.add(demand)
    await db.commit()
    return GroupDemandResponse(
        id=demand.id, schedule_id=demand.schedule_id,
        date=demand.date, group_id=demand.group_id,
        pattern_id=demand.pattern_id, min_count=demand.min_count,
    )


@router.delete("/schedules/{schedule_id}/group-demands/{demand_id}", status_code=204)
async def delete_group_demand(
    schedule_id: str,
    demand_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_schedule(schedule_id, tenant_id, db)
    result = await db.execute(
        select(GroupDemand).where(
            GroupDemand.id == demand_id,
            GroupDemand.schedule_id == schedule_id,
            GroupDemand.tenant_id == tenant_id,
        )
    )
    demand = result.scalar_one_or_none()
    if demand is None:
        raise HTTPException(status_code=404, detail="Group demand not found")
    await db.delete(demand)
    await db.commit()


@router.delete("/schedules/{schedule_id}/group-demands", status_code=204)
async def clear_group_demands(
    schedule_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    await _get_schedule(schedule_id, tenant_id, db)
    await db.execute(delete(GroupDemand).where(
        GroupDemand.schedule_id == schedule_id,
        GroupDemand.tenant_id == tenant_id,
    ))
    await db.commit()
