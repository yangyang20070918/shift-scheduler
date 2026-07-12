from __future__ import annotations

from ..context import SolverContext
from .base import BaseConstraint, ConstraintSpec, LinearConstraint

DEFAULT_WEIGHT = 40
HOURS_SCALE = 10


class P5PeriodHoursConstraint(BaseConstraint):
    priority = "P5"
    group = "personal"

    def compile(self, ctx: SolverContext) -> list[ConstraintSpec]:
        specs: list[ConstraintSpec] = []

        for m in range(ctx.num_members):
            pc = ctx.get_person_constraint(ctx.input.members[m].id)
            if pc is None:
                continue
            if pc.period_work_hours_min is None and pc.period_work_hours_max is None:
                continue

            var_keys: list[str] = []
            coefficients: list[int] = []

            for d in range(ctx.num_days):
                for k in ctx.available_patterns(m):
                    var_keys.append(ctx.x_key(m, d, k))
                    wh = ctx.input.patterns[k].work_hours
                    coefficients.append(int(wh * HOURS_SCALE))

            lb_scaled = int(pc.period_work_hours_min * HOURS_SCALE) if pc.period_work_hours_min is not None else None
            ub_scaled = int(pc.period_work_hours_max * HOURS_SCALE) if pc.period_work_hours_max is not None else None

            specs.append(LinearConstraint(
                var_keys=var_keys,
                coefficients=coefficients,
                lb=lb_scaled,
                ub=ub_scaled,
                is_hard=False,
                penalty_weight=DEFAULT_WEIGHT,
                name=f"P5_phrs_{m}",
            ))
        return specs
