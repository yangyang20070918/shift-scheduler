from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.member import Member
from ..models.rest_request import RestDayRequest
from ..models.schedule import Schedule

router = APIRouter(prefix="/api/personal", tags=["personal"])


async def get_member_by_token(
    token: str = Query(..., alias="token"),
    db: AsyncSession = Depends(get_db),
) -> Member:
    result = await db.execute(select(Member).where(Member.personal_token == token))
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=401, detail="Invalid personal token")
    return member


@router.get("/info")
async def personal_info(
    member: Member = Depends(get_member_by_token),
    db: AsyncSession = Depends(get_db),
):
    schedules_q = await db.execute(
        select(Schedule).where(
            Schedule.tenant_id == member.tenant_id,
            Schedule.status.in_(["requesting", "completed"]),
        )
    )
    schedules = schedules_q.scalars().all()

    schedule_list = []
    for s in schedules:
        req_q = await db.execute(
            select(RestDayRequest).where(
                RestDayRequest.schedule_id == s.id,
                RestDayRequest.member_id == member.id,
            )
        )
        req = req_q.scalar_one_or_none()

        schedule_list.append({
            "id": s.id,
            "name": s.name,
            "start_date": str(s.start_date),
            "num_days": s.num_days,
            "status": s.status,
            "rest_request_max_days": s.rest_request_max_days,
            "rest_request_deadline": str(s.rest_request_deadline) if s.rest_request_deadline else None,
            "my_request_status": req.status if req else None,
            "my_requested_dates": [str(d) for d in (req.requested_dates or [])] if req else [],
        })

    return {
        "member_id": member.id,
        "member_name": member.name,
        "schedules": schedule_list,
    }


@router.get("/schedules/{schedule_id}/rest-request")
async def get_rest_request(
    schedule_id: str,
    member: Member = Depends(get_member_by_token),
    db: AsyncSession = Depends(get_db),
):
    sched_q = await db.execute(
        select(Schedule).where(
            Schedule.id == schedule_id,
            Schedule.tenant_id == member.tenant_id,
        )
    )
    schedule = sched_q.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    req_q = await db.execute(
        select(RestDayRequest).where(
            RestDayRequest.schedule_id == schedule_id,
            RestDayRequest.member_id == member.id,
        )
    )
    req = req_q.scalar_one_or_none()

    return {
        "schedule_id": schedule_id,
        "schedule_name": schedule.name,
        "start_date": str(schedule.start_date),
        "num_days": schedule.num_days,
        "status": schedule.status,
        "rest_request_max_days": schedule.rest_request_max_days,
        "rest_request_deadline": str(schedule.rest_request_deadline) if schedule.rest_request_deadline else None,
        "request": {
            "requested_dates": [str(d) for d in (req.requested_dates or [])] if req else [],
            "status": req.status if req else "draft",
            "submitted_at": str(req.submitted_at) if req and req.submitted_at else None,
        } if req else {
            "requested_dates": [],
            "status": "draft",
            "submitted_at": None,
        },
    }


@router.put("/schedules/{schedule_id}/rest-request")
async def update_rest_request(
    schedule_id: str,
    body: dict,
    member: Member = Depends(get_member_by_token),
    db: AsyncSession = Depends(get_db),
):
    sched_q = await db.execute(
        select(Schedule).where(
            Schedule.id == schedule_id,
            Schedule.tenant_id == member.tenant_id,
        )
    )
    schedule = sched_q.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if schedule.status != "requesting":
        raise HTTPException(status_code=400, detail="Rest requests are not open")

    requested_dates = body.get("requested_dates", [])
    if len(requested_dates) > schedule.rest_request_max_days:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {schedule.rest_request_max_days} days allowed",
        )

    req_q = await db.execute(
        select(RestDayRequest).where(
            RestDayRequest.schedule_id == schedule_id,
            RestDayRequest.member_id == member.id,
        )
    )
    req = req_q.scalar_one_or_none()

    if req and req.status == "submitted":
        raise HTTPException(status_code=400, detail="Already submitted, cannot modify")

    if req is None:
        req = RestDayRequest(
            id=str(uuid.uuid4()),
            tenant_id=member.tenant_id,
            schedule_id=schedule_id,
            member_id=member.id,
            requested_dates=requested_dates,
            status="draft",
        )
        db.add(req)
    else:
        req.requested_dates = requested_dates

    await db.commit()

    return {
        "requested_dates": req.requested_dates,
        "status": req.status,
    }


@router.post("/schedules/{schedule_id}/rest-request/submit")
async def submit_rest_request(
    schedule_id: str,
    member: Member = Depends(get_member_by_token),
    db: AsyncSession = Depends(get_db),
):
    sched_q = await db.execute(
        select(Schedule).where(
            Schedule.id == schedule_id,
            Schedule.tenant_id == member.tenant_id,
        )
    )
    schedule = sched_q.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if schedule.status != "requesting":
        raise HTTPException(status_code=400, detail="Rest requests are not open")

    req_q = await db.execute(
        select(RestDayRequest).where(
            RestDayRequest.schedule_id == schedule_id,
            RestDayRequest.member_id == member.id,
        )
    )
    req = req_q.scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail="No request found")

    if req.status == "submitted":
        raise HTTPException(status_code=400, detail="Already submitted")

    req.status = "submitted"
    req.submitted_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "requested_dates": req.requested_dates,
        "status": "submitted",
        "submitted_at": str(req.submitted_at),
    }


@router.get("/schedules/{schedule_id}/my-schedule")
async def get_my_schedule(
    schedule_id: str,
    member: Member = Depends(get_member_by_token),
    db: AsyncSession = Depends(get_db),
):
    sched_q = await db.execute(
        select(Schedule).where(
            Schedule.id == schedule_id,
            Schedule.tenant_id == member.tenant_id,
        )
    )
    schedule = sched_q.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if schedule.status != "completed" or not schedule.assignments:
        return {
            "schedule_name": schedule.name,
            "status": schedule.status,
            "assignments": [],
        }

    my_assignments = [
        a for a in schedule.assignments if a.get("member_id") == member.id
    ]

    return {
        "schedule_name": schedule.name,
        "start_date": str(schedule.start_date),
        "num_days": schedule.num_days,
        "status": schedule.status,
        "assignments": my_assignments,
    }
