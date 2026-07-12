from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from ..models.constraint import PersonConstraint
from ..models.demand import DailyDemand, GroupDemand
from ..models.group import Group, GroupMember
from ..models.member import Member
from ..models.pattern import ForbiddenTransition, PatternChain, ShiftPattern
from ..models.schedule import FixedAssignment, Schedule


_TYPE_MAP = {
    "work": "NORMAL", "rest": "REST", "leave": "LEAVE",
    "training": "TRAINING", "meeting": "MEETING",
    "oncall": "ONCALL", "holiday": "HOLIDAY", "companion": "COMPANION",
}


async def build_solver_input(db: AsyncSession, schedule: Schedule) -> dict:
    tenant_id = schedule.tenant_id

    patterns_q = await db.execute(select(ShiftPattern).where(ShiftPattern.tenant_id == tenant_id))
    patterns = patterns_q.scalars().all()

    members_q = await db.execute(select(Member).where(Member.tenant_id == tenant_id))
    members = members_q.scalars().all()

    pc_q = await db.execute(select(PersonConstraint).where(PersonConstraint.tenant_id == tenant_id))
    person_constraints = pc_q.scalars().all()

    ft_q = await db.execute(select(ForbiddenTransition).where(ForbiddenTransition.tenant_id == tenant_id))
    forbidden = ft_q.scalars().all()

    chain_q = await db.execute(select(PatternChain).where(PatternChain.tenant_id == tenant_id))
    chains = chain_q.scalars().all()

    groups_q = await db.execute(select(Group).where(Group.tenant_id == tenant_id))
    groups = groups_q.scalars().all()

    gm_q = await db.execute(select(GroupMember).where(GroupMember.tenant_id == tenant_id))
    group_members = gm_q.scalars().all()
    group_member_map: dict[str, list[str]] = {}
    for gm in group_members:
        group_member_map.setdefault(gm.group_id, []).append(gm.member_id)

    dd_q = await db.execute(
        select(DailyDemand).where(DailyDemand.schedule_id == schedule.id)
    )
    daily_demands = dd_q.scalars().all()

    gd_q = await db.execute(
        select(GroupDemand).where(GroupDemand.schedule_id == schedule.id)
    )
    group_demands = gd_q.scalars().all()

    fa_q = await db.execute(
        select(FixedAssignment).where(FixedAssignment.schedule_id == schedule.id)
    )
    fixed_assignments = fa_q.scalars().all()

    return {
        "start_date": str(schedule.start_date),
        "num_days": schedule.num_days,
        "patterns": [
            {
                "id": p.id, "name": p.name, "type": _TYPE_MAP.get(p.type, p.type.upper()),
                "start_time": p.start_time, "end_time": p.end_time,
                "break_hours": p.break_hours, "work_hours": p.work_hours,
                "is_companion": p.is_companion, "color_code": p.color_code,
            }
            for p in patterns
        ],
        "members": [
            {"id": m.id, "name": m.name, "available_pattern_ids": m.available_pattern_ids or []}
            for m in members
        ],
        "person_constraints": [
            {
                "member_id": pc.member_id,
                "weekly_work_days_min": pc.weekly_work_days_min,
                "weekly_work_days_max": pc.weekly_work_days_max,
                "period_work_days_min": pc.period_work_days_min,
                "period_work_days_max": pc.period_work_days_max,
                "weekly_work_hours_min": pc.weekly_work_hours_min,
                "weekly_work_hours_max": pc.weekly_work_hours_max,
                "period_work_hours_min": pc.period_work_hours_min,
                "period_work_hours_max": pc.period_work_hours_max,
                "max_consecutive_work_days": pc.max_consecutive_work_days,
                "max_consecutive_rest_days": pc.max_consecutive_rest_days,
            }
            for pc in person_constraints
        ],
        "groups": [
            {"id": g.id, "name": g.name, "member_ids": group_member_map.get(g.id, [])}
            for g in groups
        ],
        "forbidden_transitions": [
            {"from_pattern_id": ft.from_pattern_id, "to_pattern_id": ft.to_pattern_id}
            for ft in forbidden
        ],
        "pattern_chains": [
            {
                "id": c.id, "trigger_pattern_id": c.trigger_pattern_id,
                "nodes": c.nodes or [], "total_length": c.total_length,
            }
            for c in chains
        ],
        "fixed_assignments": [
            {
                "member_id": fa.member_id, "date": str(fa.date),
                "type": fa.type, "pattern_id": fa.pattern_id,
            }
            for fa in fixed_assignments
        ],
        "daily_demands": [
            {"date": str(dd.date), "min_total": dd.min_total, "max_total": dd.max_total}
            for dd in daily_demands
        ],
        "group_demands": [
            {
                "date": str(gd.date), "group_id": gd.group_id,
                "pattern_id": gd.pattern_id, "min_count": gd.min_count,
            }
            for gd in group_demands
        ],
        "carry_over": [],
        "config": schedule.config or {"time_limit_seconds": 120, "week_start_day": 1},
    }


async def run_solve(db: AsyncSession, schedule_id: str):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if schedule is None:
        return

    schedule.status = "running"
    await db.commit()

    try:
        from solver_core.engine import solve
        solver_input = await build_solver_input(db, schedule)
        output = solve(solver_input)

        schedule.status = "completed"
        schedule.result_status = output.status
        schedule.solve_time_seconds = output.solve_time_seconds
        schedule.total_penalty = output.total_penalty
        schedule.health_score = output.health_score
        schedule.score_breakdown = output.score_breakdown.model_dump()
        schedule.assignments = [a.model_dump(mode="json") for a in output.assignments]
        schedule.violations = [v.model_dump(mode="json") for v in output.violations]
        schedule.warnings = [w.model_dump(mode="json") for w in output.warnings]
    except Exception as e:
        schedule.status = "failed"
        schedule.warnings = [{"warning_type": "error", "severity": "error", "message": str(e)}]

    await db.commit()
