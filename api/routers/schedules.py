from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session, get_db
from ..deps import get_tenant_id
from ..models.member import Member
from ..models.pattern import ShiftPattern
from ..models.schedule import Schedule
from ..schemas.common import ScheduleCreate, ScheduleResponse, ScheduleResultResponse

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Schedule).where(Schedule.tenant_id == tenant_id))
    schedules = result.scalars().all()
    return [
        ScheduleResponse(
            id=s.id, name=s.name, start_date=str(s.start_date),
            num_days=s.num_days, status=s.status,
            rest_request_deadline=str(s.rest_request_deadline) if s.rest_request_deadline else None,
            rest_request_max_days=s.rest_request_max_days,
            result_status=s.result_status,
            solve_time_seconds=s.solve_time_seconds,
            total_penalty=s.total_penalty,
            health_score=s.health_score,
            score_breakdown=s.score_breakdown,
        )
        for s in schedules
    ]


@router.post("", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    body: ScheduleCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    schedule = Schedule(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=body.name,
        start_date=body.start_date,
        num_days=body.num_days,
        config=body.config or {"time_limit_seconds": 120, "week_start_day": 1},
        rest_request_deadline=body.rest_request_deadline,
        rest_request_max_days=body.rest_request_max_days,
    )
    db.add(schedule)
    await db.commit()
    return ScheduleResponse(
        id=schedule.id, name=schedule.name, start_date=str(schedule.start_date),
        num_days=schedule.num_days, status=schedule.status,
        rest_request_deadline=str(schedule.rest_request_deadline) if schedule.rest_request_deadline else None,
        rest_request_max_days=schedule.rest_request_max_days,
    )


@router.post("/{schedule_id}/generate", response_model=ScheduleResponse)
async def generate_schedule(
    schedule_id: str,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id, Schedule.tenant_id == tenant_id))
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if schedule.status == "running":
        raise HTTPException(status_code=409, detail="Schedule is already running")

    schedule.status = "running"
    await db.commit()

    async def _run():
        from ..services.scheduler import run_solve
        async with async_session() as session:
            await run_solve(session, schedule_id)

    background_tasks.add_task(_run)
    return ScheduleResponse(
        id=schedule.id, name=schedule.name, start_date=str(schedule.start_date),
        num_days=schedule.num_days, status="running",
    )


@router.get("/{schedule_id}/export/excel")
async def export_excel(
    schedule_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id, Schedule.tenant_id == tenant_id))
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.status != "completed":
        raise HTTPException(status_code=400, detail="Schedule not completed")

    members_q = await db.execute(select(Member).where(Member.tenant_id == tenant_id))
    members = [{"id": m.id, "name": m.name} for m in members_q.scalars().all()]

    patterns_q = await db.execute(select(ShiftPattern).where(ShiftPattern.tenant_id == tenant_id))
    patterns = [
        {"id": p.id, "name": p.name, "color_code": p.color_code, "work_hours": p.work_hours}
        for p in patterns_q.scalars().all()
    ]

    from ..services.export_excel import generate_schedule_excel
    buf = generate_schedule_excel(
        schedule_name=schedule.name or f"Schedule {schedule_id[:8]}",
        start_date=schedule.start_date,
        num_days=schedule.num_days,
        assignments=schedule.assignments or [],
        violations=schedule.violations or [],
        warnings=schedule.warnings or [],
        score_breakdown=schedule.score_breakdown,
        health_score=schedule.health_score,
        solve_time_seconds=schedule.solve_time_seconds,
        members=members,
        patterns=patterns,
    )

    filename = f"schedule_{schedule.name or schedule_id[:8]}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{schedule_id}/compare")
async def compare_scenarios(
    schedule_id: str,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id, Schedule.tenant_id == tenant_id))
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    from ..services.scheduler import build_solver_input
    solver_input_dict = await build_solver_input(db, schedule)

    from solver_core.models import SolverInput
    from solver_core.scenario import ScenarioComparator, ALL_PROFILES

    solver_input = SolverInput(**solver_input_dict)
    comparator = ScenarioComparator()
    comparison = comparator.compare(solver_input, ALL_PROFILES)

    scenarios = []
    for sr in comparison.scenarios:
        scenarios.append({
            "name": sr.profile.name,
            "description": sr.profile.description,
            "health_score": sr.output.health_score,
            "total_penalty": sr.output.total_penalty,
            "violations_count": len(sr.output.violations),
            "score_breakdown": sr.output.score_breakdown.model_dump(),
            "solve_time_seconds": sr.output.solve_time_seconds,
        })

    return {"scenarios": scenarios}


@router.get("/{schedule_id}", response_model=ScheduleResultResponse)
async def get_schedule_result(
    schedule_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id, Schedule.tenant_id == tenant_id))
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return ScheduleResultResponse(
        id=schedule.id,
        status=schedule.status,
        result_status=schedule.result_status,
        solve_time_seconds=schedule.solve_time_seconds,
        health_score=schedule.health_score,
        score_breakdown=schedule.score_breakdown,
        assignments=schedule.assignments,
        violations=schedule.violations,
        warnings=schedule.warnings,
    )
