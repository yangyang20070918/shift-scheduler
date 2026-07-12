from __future__ import annotations

import uuid
from datetime import date as date_type, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_tenant_id
from ..models.member import Member
from ..models.rest_request import RestDayRequest
from ..models.schedule import FixedAssignment, Schedule
from ..schemas.common import RestDayRequestResponse, RestDayRequestUpdate

router = APIRouter(prefix="/api/schedules", tags=["rest-requests"])


def _format_response(req: RestDayRequest, member_name: str = "") -> dict:
    return RestDayRequestResponse(
        id=req.id,
        schedule_id=req.schedule_id,
        member_id=req.member_id,
        member_name=member_name,
        requested_dates=[str(d) for d in (req.requested_dates or [])],
        status=req.status,
        submitted_at=str(req.submitted_at) if req.submitted_at else None,
        is_auto_submitted=req.is_auto_submitted,
    ).model_dump()


@router.get("/{schedule_id}/rest-requests")
async def list_rest_requests(
    schedule_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    sched = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id, Schedule.tenant_id == tenant_id)
    )
    if sched.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    members_q = await db.execute(select(Member).where(Member.tenant_id == tenant_id))
    members = {m.id: m.name for m in members_q.scalars().all()}

    reqs_q = await db.execute(
        select(RestDayRequest).where(
            RestDayRequest.schedule_id == schedule_id,
            RestDayRequest.tenant_id == tenant_id,
        )
    )
    reqs = reqs_q.scalars().all()

    return [_format_response(r, members.get(r.member_id, "")) for r in reqs]


@router.put("/{schedule_id}/rest-requests/{member_id}")
async def update_rest_request(
    schedule_id: str,
    member_id: str,
    body: RestDayRequestUpdate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    sched_q = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id, Schedule.tenant_id == tenant_id)
    )
    schedule = sched_q.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    req_q = await db.execute(
        select(RestDayRequest).where(
            RestDayRequest.schedule_id == schedule_id,
            RestDayRequest.member_id == member_id,
            RestDayRequest.tenant_id == tenant_id,
        )
    )
    req = req_q.scalar_one_or_none()

    dates_str = [str(d) for d in body.requested_dates]

    if req is None:
        req = RestDayRequest(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            schedule_id=schedule_id,
            member_id=member_id,
            requested_dates=dates_str,
            status="draft",
        )
        db.add(req)
    else:
        req.requested_dates = dates_str

    await db.commit()

    member_q = await db.execute(select(Member).where(Member.id == member_id))
    member = member_q.scalar_one_or_none()

    return _format_response(req, member.name if member else "")


@router.post("/{schedule_id}/rest-requests/open")
async def open_rest_requests(
    schedule_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    sched_q = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id, Schedule.tenant_id == tenant_id)
    )
    schedule = sched_q.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if schedule.status not in ("draft", "requesting"):
        raise HTTPException(status_code=400, detail="Cannot open rest requests in current status")

    schedule.status = "requesting"

    members_q = await db.execute(select(Member).where(Member.tenant_id == tenant_id))
    members = members_q.scalars().all()

    for member in members:
        existing = await db.execute(
            select(RestDayRequest).where(
                RestDayRequest.schedule_id == schedule_id,
                RestDayRequest.member_id == member.id,
                RestDayRequest.tenant_id == tenant_id,
            )
        )
        if existing.scalar_one_or_none() is None:
            req = RestDayRequest(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                schedule_id=schedule_id,
                member_id=member.id,
                requested_dates=[],
                status="draft",
            )
            db.add(req)

        if not member.personal_token:
            member.personal_token = str(uuid.uuid4())

    await db.commit()
    return {"status": "requesting", "members_count": len(members)}


@router.post("/{schedule_id}/rest-requests/close")
async def close_rest_requests(
    schedule_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    sched_q = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id, Schedule.tenant_id == tenant_id)
    )
    schedule = sched_q.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    reqs_q = await db.execute(
        select(RestDayRequest).where(
            RestDayRequest.schedule_id == schedule_id,
            RestDayRequest.tenant_id == tenant_id,
        )
    )
    reqs = reqs_q.scalars().all()

    auto_submitted = 0
    fixed_created = 0

    for req in reqs:
        if req.status == "draft":
            req.status = "submitted"
            req.submitted_at = datetime.now(timezone.utc)
            req.is_auto_submitted = True
            auto_submitted += 1

        for d in (req.requested_dates or []):
            d_date = date_type.fromisoformat(str(d))
            existing_fa = await db.execute(
                select(FixedAssignment).where(
                    FixedAssignment.schedule_id == schedule_id,
                    FixedAssignment.member_id == req.member_id,
                    FixedAssignment.date == d_date,
                    FixedAssignment.tenant_id == tenant_id,
                )
            )
            if existing_fa.scalar_one_or_none() is None:
                fa = FixedAssignment(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    schedule_id=schedule_id,
                    member_id=req.member_id,
                    date=d_date,
                    type="rest",
                )
                db.add(fa)
                fixed_created += 1

    schedule.status = "draft"
    await db.commit()

    return {
        "status": "closed",
        "auto_submitted": auto_submitted,
        "fixed_assignments_created": fixed_created,
    }
