from __future__ import annotations

from datetime import date

from .context import SolverContext
from .models import Assignment, Violation


class ExplainEngine:

    def explain(self, ctx: SolverContext, assignments: list[Assignment], violations: list[Violation]) -> list[Violation]:
        schedule = self._build_schedule(ctx, assignments)

        for v in violations:
            factors = []
            suggestions = []
            confidence = "medium"

            if v.constraint_type in ("daily_demand_min", "daily_demand_max"):
                factors, suggestions, confidence = self._explain_demand(ctx, schedule, v)
            elif v.constraint_type in ("period_days_min", "period_days_max"):
                factors, suggestions, confidence = self._explain_period_days(ctx, schedule, v)
            elif v.constraint_type in ("weekly_days_min", "weekly_days_max"):
                factors, suggestions, confidence = self._explain_weekly_days(ctx, schedule, v)
            elif v.constraint_type == "consecutive_work":
                factors, suggestions, confidence = self._explain_consecutive_work(ctx, schedule, v)
            elif v.constraint_type == "consecutive_rest":
                factors, suggestions, confidence = self._explain_consecutive_rest(ctx, schedule, v)
            elif v.constraint_type in ("period_hours_min", "period_hours_max"):
                factors, suggestions, confidence = self._explain_period_hours(ctx, schedule, v)

            v.contributing_factors = factors
            v.suggestions = suggestions

        return violations

    def _build_schedule(self, ctx, assignments):
        schedule: dict[str, list[Assignment | None]] = {
            m.id: [None] * ctx.num_days for m in ctx.input.members
        }
        for a in assignments:
            if a.date in ctx.day_dates:
                d = ctx.day_dates.index(a.date)
                schedule[a.member_id][d] = a
        return schedule

    def _explain_demand(self, ctx, schedule, v):
        factors = []
        suggestions = []

        if v.target_date is None:
            return factors, suggestions, "low"

        d = ctx.day_dates.index(v.target_date)

        resting_members = []
        fixed_rest_members = []
        for m in ctx.input.members:
            a = schedule[m.id][d]
            if a and a.is_rest:
                resting_members.append(m.id)
                fa = ctx.get_fixed(m.id, v.target_date)
                if fa and fa.type == "rest":
                    fixed_rest_members.append(m.id)

        if fixed_rest_members:
            factors.append(f"固定休息メンバー({len(fixed_rest_members)}人): {', '.join(fixed_rest_members[:3])}")

        non_fixed_rest = [m for m in resting_members if m not in fixed_rest_members]
        if non_fixed_rest:
            factors.append(f"自動休息メンバー({len(non_fixed_rest)}人): {', '.join(non_fixed_rest[:3])}")

        if v.constraint_type == "daily_demand_min":
            if non_fixed_rest:
                suggestions.append(f"{v.target_date}の休息人数を減らすことを検討してください")
            if fixed_rest_members:
                suggestions.append(f"この日は{len(fixed_rest_members)}人が固定休息です。固定割当の調整を検討してください")
            suggestions.append("または、この日の最低必要人数を下げてください")

        confidence = "high" if fixed_rest_members else "medium"
        return factors, suggestions, confidence

    def _explain_period_days(self, ctx, schedule, v):
        factors = []
        suggestions = []
        mid = v.target_member_id

        if mid is None:
            return factors, suggestions, "low"

        rest_days = []
        work_days = []
        for d in range(ctx.num_days):
            a = schedule[mid][d]
            if a and a.is_rest:
                rest_days.append(d)
            elif a and not a.is_rest:
                work_days.append(d)

        fixed_rests = [
            d for d in rest_days
            if ctx.get_fixed(mid, ctx.day_dates[d]) and ctx.get_fixed(mid, ctx.day_dates[d]).type == "rest"
        ]

        if v.constraint_type == "period_days_min":
            factors.append(f"実績出勤{len(work_days)}日、休息{len(rest_days)}日")
            if fixed_rests:
                factors.append(f"うち{len(fixed_rests)}日は固定休息")
            suggestions.append("休息日数を減らすか、期間出勤下限を緩和してください")
            if fixed_rests:
                suggestions.append(f"固定休息日数（現在{len(fixed_rests)}日）の削減を検討してください")
        else:
            factors.append(f"実績出勤{len(work_days)}日（上限超過）")
            pc = ctx.get_person_constraint(mid)
            if pc and pc.max_consecutive_work_days:
                factors.append(f"連続出勤上限({pc.max_consecutive_work_days}日)が休息挿入を制限している可能性があります")
            suggestions.append("休息日数を増やすか、期間出勤上限を緩和してください")

        confidence = "high" if fixed_rests else "medium"
        return factors, suggestions, confidence

    def _explain_weekly_days(self, ctx, schedule, v):
        factors = []
        suggestions = []
        mid = v.target_member_id

        if mid is None or v.target_date is None:
            return factors, suggestions, "low"

        d_start = ctx.day_dates.index(v.target_date)
        weeks = ctx.week_indices()
        target_week = None
        for w in weeks:
            if d_start in w:
                target_week = w
                break

        if target_week is None:
            return factors, suggestions, "low"

        week_work = sum(
            1 for d in target_week
            if schedule[mid][d] and not schedule[mid][d].is_rest
        )
        week_rest = len(target_week) - week_work

        factors.append(f"当週の出勤{week_work}日/休息{week_rest}日（全{len(target_week)}日）")

        if len(target_week) < 7:
            factors.append(f"注意：当週は{len(target_week)}日のみ（期間境界による短縮週）")
            suggestions.append("期間境界の短縮週では制約の緩和が必要な場合があります")

        if v.constraint_type == "weekly_days_min":
            suggestions.append("当週の休息日数を減らすか、週出勤下限を下げてください")
        else:
            suggestions.append("当週の休息日数を増やすか、週出勤上限を上げてください")

        return factors, suggestions, "medium"

    def _explain_consecutive_work(self, ctx, schedule, v):
        factors = []
        suggestions = []
        mid = v.target_member_id

        if mid is None or v.target_date is None:
            return factors, suggestions, "low"

        d_end = ctx.day_dates.index(v.target_date)
        streak_len = int(v.actual_value) if v.actual_value else 0

        d_start = max(0, d_end - streak_len + 1)
        streak_dates = [ctx.day_dates[d] for d in range(d_start, d_end + 1)]
        factors.append(f"連続出勤区間: {streak_dates[0]}〜{streak_dates[-1]}（{streak_len}日）")

        demand_days = []
        for d in range(d_start, d_end + 1):
            dd = ctx.get_daily_demand(ctx.day_dates[d])
            if dd and dd.min_total > 0:
                demand_days.append(d)
        if demand_days:
            factors.append(f"この区間の{len(demand_days)}日に最低人力需要があります")

        co = ctx.get_carry_over(mid)
        if co and co.trailing_work_days > 0 and d_start == 0:
            factors.append(f"前期引継: 既に連続{co.trailing_work_days}日出勤済み")

        suggestions.append("連続出勤区間に休息日を挿入してください")
        if demand_days:
            suggestions.append("または、この区間の毎日最低必要人数を下げてください")

        confidence = "high" if (co and co.trailing_work_days > 0) else "medium"
        return factors, suggestions, confidence

    def _explain_consecutive_rest(self, ctx, schedule, v):
        factors = []
        suggestions = []
        mid = v.target_member_id

        if mid is None or v.target_date is None:
            return factors, suggestions, "low"

        d_end = ctx.day_dates.index(v.target_date)
        streak_len = int(v.actual_value) if v.actual_value else 0
        d_start = max(0, d_end - streak_len + 1)

        factors.append(f"連続休息区間: {ctx.day_dates[d_start]}〜{ctx.day_dates[d_end]}（{streak_len}日）")

        fixed_in_streak = []
        for d in range(d_start, d_end + 1):
            fa = ctx.get_fixed(mid, ctx.day_dates[d])
            if fa and fa.type == "rest":
                fixed_in_streak.append(ctx.day_dates[d])
        if fixed_in_streak:
            factors.append(f"うち{len(fixed_in_streak)}日は固定休息")

        suggestions.append("連続休息区間に出勤日を挿入してください")
        if fixed_in_streak:
            suggestions.append("または、固定休息設定の調整を検討してください")

        confidence = "high" if fixed_in_streak else "medium"
        return factors, suggestions, confidence

    def _explain_period_hours(self, ctx, schedule, v):
        factors = []
        suggestions = []
        mid = v.target_member_id

        if mid is None:
            return factors, suggestions, "low"

        total_hours = 0.0
        pattern_counts: dict[str, int] = {}
        for d in range(ctx.num_days):
            a = schedule[mid][d]
            if a and not a.is_rest and a.pattern_id:
                if a.pattern_id in ctx._pattern_id_to_idx:
                    k = ctx.pattern_idx(a.pattern_id)
                    h = ctx.input.patterns[k].work_hours
                    total_hours += h
                    pattern_counts[a.pattern_id] = pattern_counts.get(a.pattern_id, 0) + 1

        factors.append(f"総労働時間: {total_hours}h")
        if pattern_counts:
            top_patterns = sorted(pattern_counts.items(), key=lambda x: -x[1])[:3]
            factors.append("パターン分布: " + ", ".join(f"{pid}×{cnt}" for pid, cnt in top_patterns))

        if v.constraint_type == "period_hours_min":
            suggestions.append("出勤日数を増やすか、労働時間の長いパターンを選択してください")
        else:
            suggestions.append("出勤日数を減らすか、労働時間の短いパターンを選択してください")

        return factors, suggestions, "medium"
