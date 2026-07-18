from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session
from ..models.member import Member
from ..models.rest_request import RestDayRequest
from ..models.schedule import FixedAssignment, Schedule

logger = logging.getLogger(__name__)


async def auto_close_expired_rest_requests(db: AsyncSession) -> dict:
    today = date.today()

    schedules_q = await db.execute(
        select(Schedule).where(
            Schedule.status == "requesting",
            Schedule.rest_request_deadline != None,  # noqa: E711
            Schedule.rest_request_deadline <= today,
        )
    )
    schedules = schedules_q.scalars().all()

    total_auto_submitted = 0
    total_fixed_created = 0
    closed_schedules = 0

    for schedule in schedules:
        reqs_q = await db.execute(
            select(RestDayRequest).where(
                RestDayRequest.schedule_id == schedule.id,
                RestDayRequest.tenant_id == schedule.tenant_id,
            )
        )
        reqs = reqs_q.scalars().all()

        for req in reqs:
            if req.status == "draft":
                req.status = "submitted"
                req.submitted_at = datetime.now(timezone.utc)
                req.is_auto_submitted = True
                total_auto_submitted += 1

            for d in (req.requested_dates or []):
                d_date = date.fromisoformat(str(d))
                existing_fa = await db.execute(
                    select(FixedAssignment).where(
                        FixedAssignment.schedule_id == schedule.id,
                        FixedAssignment.member_id == req.member_id,
                        FixedAssignment.date == d_date,
                        FixedAssignment.tenant_id == schedule.tenant_id,
                    )
                )
                if existing_fa.scalar_one_or_none() is None:
                    fa = FixedAssignment(
                        id=str(uuid.uuid4()),
                        tenant_id=schedule.tenant_id,
                        schedule_id=schedule.id,
                        member_id=req.member_id,
                        date=d_date,
                        type="rest",
                    )
                    db.add(fa)
                    total_fixed_created += 1

        schedule.status = "draft"
        closed_schedules += 1

    if closed_schedules > 0:
        await db.commit()
        logger.info(
            "Auto-closed %d schedules: %d auto-submitted, %d fixed assignments created",
            closed_schedules, total_auto_submitted, total_fixed_created,
        )

    return {
        "closed_schedules": closed_schedules,
        "auto_submitted": total_auto_submitted,
        "fixed_assignments_created": total_fixed_created,
    }


async def cleanup_old_schedule_data(db: AsyncSession, retention_days: int = 180) -> dict:
    cutoff = date.today() - timedelta(days=retention_days)

    old_q = await db.execute(
        select(Schedule).where(
            Schedule.status == "completed",
            Schedule.start_date < cutoff,
        )
    )
    old_schedules = old_q.scalars().all()

    cleaned = 0
    for schedule in old_schedules:
        if schedule.assignments:
            schedule.assignments = None
            cleaned += 1

    if cleaned > 0:
        await db.commit()
        logger.info("Cleaned assignment data from %d old schedules (older than %s)", cleaned, cutoff)

    return {"cleaned_schedules": cleaned, "cutoff_date": str(cutoff)}


async def run_periodic_tasks(interval_seconds: int = 3600):
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            async with async_session() as db:
                await auto_close_expired_rest_requests(db)
                await cleanup_old_schedule_data(db)
        except Exception:
            logger.exception("Periodic task error")
