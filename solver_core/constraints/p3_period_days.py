from __future__ import annotations

from ..context import SolverContext
from .base import BaseConstraint, ConstraintSpec, LinearConstraint

DEFAULT_WEIGHT = 50


class P3PeriodDaysConstraint(BaseConstraint):
    priority = "P3"
    group = "personal"

    def compile(self, ctx: SolverContext) -> list[ConstraintSpec]:
        specs: list[ConstraintSpec] = []

        for m in range(ctx.num_members):
            pc = ctx.get_person_constraint(ctx.input.members[m].id)
            if pc is None:
                continue
            if pc.period_work_days_min is None and pc.period_work_days_max is None:
                continue

            var_keys: list[str] = []
            for d in range(ctx.num_days):
                for k in ctx.available_patterns(m):
                    var_keys.append(ctx.x_key(m, d, k))

            specs.append(LinearConstraint(
                var_keys=var_keys,
                coefficients=[1] * len(var_keys),
                lb=pc.period_work_days_min,
                ub=pc.period_work_days_max,
                is_hard=False,
                penalty_weight=DEFAULT_WEIGHT,
                name=f"P3_pdays_{m}",
            ))
        return specs
