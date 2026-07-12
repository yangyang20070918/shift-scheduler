from __future__ import annotations

from .context import SolverContext
from .models import Assignment, Violation


class ViolationAnalyzer:

    def analyze(self, ctx: SolverContext, assignments: list[Assignment]) -> list[Violation]:
        violations: list[Violation] = []
        member_schedule = self._build_schedule(ctx, assignments)

        self._check_demand(ctx, member_schedule, violations)
        self._check_person_constraints(ctx, member_schedule, violations)
        self._check_consecutive(ctx, member_schedule, violations)
        self._check_group_demand(ctx, member_schedule, violations)
        return violations

    def _build_schedule(self, ctx, assignments):
        schedule: dict[str, list[Assignment]] = {
            m.id: [None] * ctx.num_days for m in ctx.input.members
        }
        for a in assignments:
            if a.date in ctx.day_dates:
                d = ctx.day_dates.index(a.date)
                schedule[a.member_id][d] = a
        return schedule

    def _check_demand(self, ctx, schedule, violations):
        for d in range(ctx.num_days):
            dd = ctx.get_daily_demand(ctx.day_dates[d])
            if dd is None:
                continue
            working = sum(
                1 for mid in schedule
                if schedule[mid][d] and not schedule[mid][d].is_rest
            )
            if working < dd.min_total:
                violations.append(Violation(
                    priority="P9", constraint_group="demand",
                    constraint_type="daily_demand_min",
                    target_date=ctx.day_dates[d],
                    setting_value=str(dd.min_total),
                    actual_value=str(working),
                ))
            if working > dd.max_total:
                violations.append(Violation(
                    priority="P9", constraint_group="demand",
                    constraint_type="daily_demand_max",
                    target_date=ctx.day_dates[d],
                    setting_value=str(dd.max_total),
                    actual_value=str(working),
                ))

    def _check_person_constraints(self, ctx, schedule, violations):
        weeks = ctx.week_indices()

        for m_idx in range(ctx.num_members):
            mid = ctx.input.members[m_idx].id
            pc = ctx.get_person_constraint(mid)
            if pc is None:
                continue

            days_worked = sum(
                1 for d in range(ctx.num_days)
                if schedule[mid][d] and not schedule[mid][d].is_rest
            )

            if pc.period_work_days_min is not None and days_worked < pc.period_work_days_min:
                violations.append(Violation(
                    priority="P3", constraint_group="personal",
                    constraint_type="period_days_min",
                    target_member_id=mid,
                    setting_value=str(pc.period_work_days_min),
                    actual_value=str(days_worked),
                ))
            if pc.period_work_days_max is not None and days_worked > pc.period_work_days_max:
                violations.append(Violation(
                    priority="P3", constraint_group="personal",
                    constraint_type="period_days_max",
                    target_member_id=mid,
                    setting_value=str(pc.period_work_days_max),
                    actual_value=str(days_worked),
                ))

            total_hours = sum(
                self._work_hours(ctx, schedule[mid][d])
                for d in range(ctx.num_days)
            )
            if pc.period_work_hours_min is not None and total_hours < pc.period_work_hours_min:
                violations.append(Violation(
                    priority="P5", constraint_group="personal",
                    constraint_type="period_hours_min",
                    target_member_id=mid,
                    setting_value=str(pc.period_work_hours_min),
                    actual_value=str(total_hours),
                ))
            if pc.period_work_hours_max is not None and total_hours > pc.period_work_hours_max:
                violations.append(Violation(
                    priority="P5", constraint_group="personal",
                    constraint_type="period_hours_max",
                    target_member_id=mid,
                    setting_value=str(pc.period_work_hours_max),
                    actual_value=str(total_hours),
                ))

            for wi, week_days in enumerate(weeks):
                wk_worked = sum(
                    1 for d in week_days
                    if schedule[mid][d] and not schedule[mid][d].is_rest
                )
                if pc.weekly_work_days_min is not None and wk_worked < pc.weekly_work_days_min:
                    violations.append(Violation(
                        priority="P2", constraint_group="personal",
                        constraint_type="weekly_days_min",
                        target_member_id=mid,
                        target_date=ctx.day_dates[week_days[0]],
                        setting_value=str(pc.weekly_work_days_min),
                        actual_value=str(wk_worked),
                    ))
                if pc.weekly_work_days_max is not None and wk_worked > pc.weekly_work_days_max:
                    violations.append(Violation(
                        priority="P2", constraint_group="personal",
                        constraint_type="weekly_days_max",
                        target_member_id=mid,
                        target_date=ctx.day_dates[week_days[0]],
                        setting_value=str(pc.weekly_work_days_max),
                        actual_value=str(wk_worked),
                    ))

                wk_hours = sum(
                    self._work_hours(ctx, schedule[mid][d]) for d in week_days
                )
                if pc.weekly_work_hours_min is not None and wk_hours < pc.weekly_work_hours_min:
                    violations.append(Violation(
                        priority="P4", constraint_group="personal",
                        constraint_type="weekly_hours_min",
                        target_member_id=mid,
                        target_date=ctx.day_dates[week_days[0]],
                        setting_value=str(pc.weekly_work_hours_min),
                        actual_value=str(wk_hours),
                    ))
                if pc.weekly_work_hours_max is not None and wk_hours > pc.weekly_work_hours_max:
                    violations.append(Violation(
                        priority="P4", constraint_group="personal",
                        constraint_type="weekly_hours_max",
                        target_member_id=mid,
                        target_date=ctx.day_dates[week_days[0]],
                        setting_value=str(pc.weekly_work_hours_max),
                        actual_value=str(wk_hours),
                    ))

    def _check_consecutive(self, ctx, schedule, violations):
        for m_idx in range(ctx.num_members):
            mid = ctx.input.members[m_idx].id
            pc = ctx.get_person_constraint(mid)
            if pc is None:
                continue

            if pc.max_consecutive_work_days is not None:
                streak = 0
                co = ctx.get_carry_over(mid)
                if co:
                    streak = co.trailing_work_days
                for d in range(ctx.num_days):
                    a = schedule[mid][d]
                    if a and not a.is_rest:
                        streak += 1
                        if streak > pc.max_consecutive_work_days:
                            violations.append(Violation(
                                priority="P6", constraint_group="personal",
                                constraint_type="consecutive_work",
                                target_member_id=mid,
                                target_date=ctx.day_dates[d],
                                setting_value=str(pc.max_consecutive_work_days),
                                actual_value=str(streak),
                            ))
                    else:
                        streak = 0

            if pc.max_consecutive_rest_days is not None:
                streak = 0
                co = ctx.get_carry_over(mid)
                if co:
                    streak = co.trailing_rest_days
                for d in range(ctx.num_days):
                    a = schedule[mid][d]
                    if a is None or a.is_rest:
                        streak += 1
                        if streak > pc.max_consecutive_rest_days:
                            violations.append(Violation(
                                priority="P7", constraint_group="personal",
                                constraint_type="consecutive_rest",
                                target_member_id=mid,
                                target_date=ctx.day_dates[d],
                                setting_value=str(pc.max_consecutive_rest_days),
                                actual_value=str(streak),
                            ))
                    else:
                        streak = 0

    def _check_group_demand(self, ctx, schedule, violations):
        for gd in ctx.input.group_demands:
            if gd.date not in ctx.day_dates:
                continue
            d = ctx.day_dates.index(gd.date)
            group_members = ctx.group_member_indices(gd.group_id)

            count = 0
            for m in group_members:
                mid = ctx.input.members[m].id
                a = schedule[mid][d]
                if a and not a.is_rest and a.pattern_id == gd.pattern_id:
                    count += 1

            if count < gd.min_count:
                violations.append(Violation(
                    priority="P8", constraint_group="group",
                    constraint_type="group_demand_min",
                    target_date=gd.date,
                    setting_value=f"{gd.group_id}:{gd.pattern_id}>={gd.min_count}",
                    actual_value=str(count),
                ))

    def _work_hours(self, ctx, assignment) -> float:
        if assignment is None or assignment.is_rest or assignment.pattern_id is None:
            return 0.0
        if assignment.pattern_id in ctx._pattern_id_to_idx:
            k = ctx.pattern_idx(assignment.pattern_id)
            return ctx.input.patterns[k].work_hours
        return 0.0
