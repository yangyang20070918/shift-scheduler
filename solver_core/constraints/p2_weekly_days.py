from __future__ import annotations

from ..context import SolverContext
from .base import BaseConstraint, ConstraintSpec, LinearConstraint

DEFAULT_WEIGHT = 50


class P2WeeklyDaysConstraint(BaseConstraint):
    priority = "P2"
    group = "personal"

    def compile(self, ctx: SolverContext) -> list[ConstraintSpec]:
        specs: list[ConstraintSpec] = []
        weeks = ctx.week_indices()

        for m in range(ctx.num_members):
            pc = ctx.get_person_constraint(ctx.input.members[m].id)
            if pc is None:
                continue
            if pc.weekly_work_days_min is None and pc.weekly_work_days_max is None:
                continue

            co = ctx.get_carry_over(ctx.input.members[m].id)

            for wi, week_days in enumerate(weeks):
                var_keys: list[str] = []
                for d in week_days:
                    for k in ctx.available_patterns(m):
                        var_keys.append(ctx.x_key(m, d, k))

                lb = pc.weekly_work_days_min
                ub = pc.weekly_work_days_max

                if wi == 0 and co is not None and co.last_week_work_days > 0:
                    carry = co.last_week_work_days
                    lb = max(0, lb - carry) if lb is not None else None
                    ub = max(0, ub - carry) if ub is not None else None

                if lb is None and ub is None:
                    continue

                specs.append(LinearConstraint(
                    var_keys=var_keys,
                    coefficients=[1] * len(var_keys),
                    lb=lb,
                    ub=ub,
                    is_hard=False,
                    penalty_weight=DEFAULT_WEIGHT,
                    name=f"P2_wkdays_{m}_{wi}",
                ))
        return specs
