from __future__ import annotations

from ..context import SolverContext
from .base import BaseConstraint, ConstraintSpec, LinearConstraint

DEFAULT_WEIGHT = 40
HOURS_SCALE = 10


class P4WeeklyHoursConstraint(BaseConstraint):
    priority = "P4"
    group = "personal"

    def compile(self, ctx: SolverContext) -> list[ConstraintSpec]:
        specs: list[ConstraintSpec] = []
        weeks = ctx.week_indices()

        for m in range(ctx.num_members):
            pc = ctx.get_person_constraint(ctx.input.members[m].id)
            if pc is None:
                continue
            if pc.weekly_work_hours_min is None and pc.weekly_work_hours_max is None:
                continue

            co = ctx.get_carry_over(ctx.input.members[m].id)

            for wi, week_days in enumerate(weeks):
                var_keys: list[str] = []
                coefficients: list[int] = []

                for d in week_days:
                    for k in ctx.available_patterns(m):
                        var_keys.append(ctx.x_key(m, d, k))
                        wh = ctx.input.patterns[k].work_hours
                        coefficients.append(int(wh * HOURS_SCALE))

                lb = pc.weekly_work_hours_min
                ub = pc.weekly_work_hours_max
                carry_hours = 0.0

                if wi == 0 and co is not None and co.last_week_work_hours > 0:
                    carry_hours = co.last_week_work_hours

                lb_scaled = int((lb - carry_hours) * HOURS_SCALE) if lb is not None else None
                ub_scaled = int((ub - carry_hours) * HOURS_SCALE) if ub is not None else None

                if lb_scaled is not None:
                    lb_scaled = max(0, lb_scaled)
                if ub_scaled is not None:
                    ub_scaled = max(0, ub_scaled)

                if lb_scaled is None and ub_scaled is None:
                    continue

                specs.append(LinearConstraint(
                    var_keys=var_keys,
                    coefficients=coefficients,
                    lb=lb_scaled,
                    ub=ub_scaled,
                    is_hard=False,
                    penalty_weight=DEFAULT_WEIGHT,
                    name=f"P4_wkhrs_{m}_{wi}",
                ))
        return specs
