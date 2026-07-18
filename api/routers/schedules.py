from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session, get_db
from ..deps import get_tenant_id
from ..models.demand import DailyDemand, GroupDemand, PatternDemand
from ..models.group import Group, GroupMember
from ..models.member import Member
from ..models.pattern import ShiftPattern
from ..models.schedule import Schedule
from ..schemas.common import ScheduleCreate, ScheduleUpdate, ScheduleResponse, ScheduleResultResponse

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


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    body: ScheduleUpdate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id, Schedule.tenant_id == tenant_id))
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    schedule.name = body.name
    await db.commit()
    return ScheduleResponse(
        id=schedule.id, name=schedule.name, start_date=str(schedule.start_date),
        num_days=schedule.num_days, status=schedule.status,
        rest_request_deadline=str(schedule.rest_request_deadline) if schedule.rest_request_deadline else None,
        rest_request_max_days=schedule.rest_request_max_days,
        result_status=schedule.result_status,
        solve_time_seconds=schedule.solve_time_seconds,
        total_penalty=schedule.total_penalty,
        health_score=schedule.health_score,
        score_breakdown=schedule.score_breakdown,
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


async def _load_export_data(schedule_id: str, tenant_id: str, db: AsyncSession):
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
        {"id": p.id, "name": p.name, "type": p.type, "color_code": p.color_code, "work_hours": p.work_hours}
        for p in patterns_q.scalars().all()
    ]

    dd_q = await db.execute(select(DailyDemand).where(DailyDemand.schedule_id == schedule_id, DailyDemand.tenant_id == tenant_id))
    daily_demands = [{"date": str(d.date), "min_total": d.min_total, "max_total": d.max_total} for d in dd_q.scalars().all()]

    pd_q = await db.execute(select(PatternDemand).where(PatternDemand.schedule_id == schedule_id, PatternDemand.tenant_id == tenant_id))
    pattern_demands = [{"date": str(d.date), "pattern_id": d.pattern_id, "min_count": d.min_count} for d in pd_q.scalars().all()]

    gd_q = await db.execute(select(GroupDemand).where(GroupDemand.schedule_id == schedule_id, GroupDemand.tenant_id == tenant_id))
    group_demands = [{"date": str(d.date), "group_id": d.group_id, "pattern_id": d.pattern_id, "min_count": d.min_count} for d in gd_q.scalars().all()]

    groups_q = await db.execute(select(Group).where(Group.tenant_id == tenant_id))
    groups_list = groups_q.scalars().all()
    groups = []
    for g in groups_list:
        gm_q = await db.execute(select(GroupMember).where(GroupMember.group_id == g.id, GroupMember.tenant_id == tenant_id))
        member_ids = [gm.member_id for gm in gm_q.scalars().all()]
        groups.append({"id": g.id, "name": g.name, "member_ids": member_ids})

    return {
        "schedule": schedule,
        "members": members,
        "patterns": patterns,
        "daily_demands": daily_demands,
        "pattern_demands": pattern_demands,
        "group_demands": group_demands,
        "groups": groups,
    }


@router.get("/{schedule_id}/export/excel")
async def export_excel(
    schedule_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    data = await _load_export_data(schedule_id, tenant_id, db)
    schedule = data["schedule"]

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
        members=data["members"],
        patterns=data["patterns"],
        daily_demands=data["daily_demands"],
        pattern_demands=data["pattern_demands"],
        group_demands=data["group_demands"],
        groups=data["groups"],
    )

    filename = f"schedule_{schedule.name or schedule_id[:8]}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{schedule_id}/export/pdf")
async def export_pdf(
    schedule_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    data = await _load_export_data(schedule_id, tenant_id, db)
    schedule = data["schedule"]

    from ..services.export_pdf import generate_schedule_pdf
    buf = generate_schedule_pdf(
        schedule_name=schedule.name or f"Schedule {schedule_id[:8]}",
        start_date=schedule.start_date,
        num_days=schedule.num_days,
        assignments=schedule.assignments or [],
        violations=schedule.violations or [],
        warnings=schedule.warnings or [],
        score_breakdown=schedule.score_breakdown,
        health_score=schedule.health_score,
        solve_time_seconds=schedule.solve_time_seconds,
        members=data["members"],
        patterns=data["patterns"],
        daily_demands=data["daily_demands"],
        pattern_demands=data["pattern_demands"],
        group_demands=data["group_demands"],
        groups=data["groups"],
    )

    filename = f"schedule_{schedule.name or schedule_id[:8]}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
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
        assignments = [a.model_dump() for a in sr.output.assignments] if sr.output.assignments else []
        for a in assignments:
            if "date" in a and hasattr(a["date"], "isoformat"):
                a["date"] = a["date"].isoformat()
        scenarios.append({
            "name": sr.profile.name,
            "description": sr.profile.description,
            "health_score": sr.output.health_score,
            "total_penalty": sr.output.total_penalty,
            "violations_count": len(sr.output.violations),
            "score_breakdown": sr.output.score_breakdown.model_dump(),
            "solve_time_seconds": sr.output.solve_time_seconds,
            "assignments": assignments,
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
        name=schedule.name,
        start_date=str(schedule.start_date),
        num_days=schedule.num_days,
        status=schedule.status,
        result_status=schedule.result_status,
        solve_time_seconds=schedule.solve_time_seconds,
        health_score=schedule.health_score,
        score_breakdown=schedule.score_breakdown,
        assignments=schedule.assignments,
        violations=schedule.violations,
        warnings=schedule.warnings,
    )


@router.post("/{schedule_id}/import/preview")
async def preview_schedule_import(
    schedule_id: str,
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id, Schedule.tenant_id == tenant_id))
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    content = await file.read()
    from ..services.import_excel import parse_schedule_result_excel
    imported = parse_schedule_result_excel(content)

    members_q = await db.execute(select(Member).where(Member.tenant_id == tenant_id))
    member_map = {m.name: m.id for m in members_q.scalars().all()}

    patterns_q = await db.execute(select(ShiftPattern).where(ShiftPattern.tenant_id == tenant_id))
    pattern_map = {p.name: p.id for p in patterns_q.scalars().all()}

    from datetime import timedelta
    start = schedule.start_date
    dates = [start + timedelta(days=i) for i in range(schedule.num_days)]
    date_label_to_iso: dict[str, str] = {}
    weekday_jp = ["月", "火", "水", "木", "金", "土", "日"]
    for d in dates:
        wd = weekday_jp[d.weekday()]
        label = f"{d.month}/{d.day}({wd})"
        date_label_to_iso[label] = str(d)

    current_assignments = schedule.assignments or []
    current_map: dict[tuple[str, str], dict] = {}
    for a in current_assignments:
        current_map[(a["member_id"], a["date"])] = a

    changes = []
    warnings = []
    for imp in imported:
        mid = member_map.get(imp["member_name"])
        if mid is None:
            warnings.append(f"メンバー「{imp['member_name']}」が見つかりません")
            continue
        iso_date = date_label_to_iso.get(imp["date_label"])
        if iso_date is None:
            warnings.append(f"日付「{imp['date_label']}」がスケジュール期間外です")
            continue

        cur = current_map.get((mid, iso_date))
        cur_pattern_name = cur.get("pattern_name", "") if cur else ""
        cur_is_rest = cur.get("is_rest", False) if cur else False

        new_is_rest = imp["is_rest"]
        new_pattern_name = imp["pattern_name"]

        if new_is_rest and cur_is_rest:
            continue
        if not new_is_rest and not cur_is_rest and new_pattern_name == cur_pattern_name:
            continue

        pid = None
        if not new_is_rest:
            pid = pattern_map.get(new_pattern_name) if new_pattern_name else None
            if new_pattern_name and pid is None:
                warnings.append(f"パターン「{new_pattern_name}」が見つかりません（{imp['member_name']} / {imp['date_label']}）")
                continue

        changes.append({
            "member_id": mid,
            "member_name": imp["member_name"],
            "date": iso_date,
            "date_label": imp["date_label"],
            "before": {"pattern_name": "休" if cur_is_rest else cur_pattern_name, "is_rest": cur_is_rest},
            "after": {"pattern_name": "休" if new_is_rest else new_pattern_name, "is_rest": new_is_rest, "pattern_id": pid},
        })

    return {"changes": changes, "warnings": warnings, "total_imported": len(imported)}


@router.post("/{schedule_id}/import/execute")
async def execute_schedule_import(
    schedule_id: str,
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id, Schedule.tenant_id == tenant_id))
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    content = await file.read()
    from ..services.import_excel import parse_schedule_result_excel
    imported = parse_schedule_result_excel(content)

    members_q = await db.execute(select(Member).where(Member.tenant_id == tenant_id))
    member_map = {m.name: m.id for m in members_q.scalars().all()}
    member_id_to_name = {m.id: m.name for m in (await db.execute(select(Member).where(Member.tenant_id == tenant_id))).scalars().all()}

    patterns_q = await db.execute(select(ShiftPattern).where(ShiftPattern.tenant_id == tenant_id))
    all_patterns = list(patterns_q.scalars().all())
    pattern_name_to_id = {p.name: p.id for p in all_patterns}
    pattern_id_to_hours = {p.id: p.work_hours for p in all_patterns}

    from datetime import timedelta
    start = schedule.start_date
    dates = [start + timedelta(days=i) for i in range(schedule.num_days)]
    weekday_jp = ["月", "火", "水", "木", "金", "土", "日"]
    date_label_to_iso: dict[str, str] = {}
    for d in dates:
        wd = weekday_jp[d.weekday()]
        date_label_to_iso[f"{d.month}/{d.day}({wd})"] = str(d)

    current_assignments = list(schedule.assignments or [])
    assignment_map: dict[tuple[str, str], int] = {}
    for idx, a in enumerate(current_assignments):
        assignment_map[(a["member_id"], a["date"])] = idx

    applied = 0
    for imp in imported:
        mid = member_map.get(imp["member_name"])
        if mid is None:
            continue
        iso_date = date_label_to_iso.get(imp["date_label"])
        if iso_date is None:
            continue

        new_is_rest = imp["is_rest"]
        new_pattern_name = imp["pattern_name"]
        pid = pattern_name_to_id.get(new_pattern_name) if new_pattern_name else None
        if not new_is_rest and new_pattern_name and pid is None:
            continue

        new_assignment = {
            "member_id": mid,
            "member_name": member_id_to_name.get(mid, imp["member_name"]),
            "date": iso_date,
            "pattern_id": pid,
            "pattern_name": new_pattern_name or "",
            "is_rest": new_is_rest,
        }

        key = (mid, iso_date)
        if key in assignment_map:
            idx = assignment_map[key]
            old = current_assignments[idx]
            if old.get("is_rest") != new_is_rest or old.get("pattern_name") != (new_pattern_name or ""):
                current_assignments[idx] = new_assignment
                applied += 1
        else:
            current_assignments.append(new_assignment)
            assignment_map[key] = len(current_assignments) - 1
            applied += 1

    schedule.assignments = current_assignments
    schedule.status = "completed"
    await db.commit()

    return {"applied": applied, "total_assignments": len(current_assignments)}
