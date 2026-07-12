from __future__ import annotations

from ..context import SolverContext
from .base import BaseConstraint, ConstraintSpec, LinearConstraint

DEFAULT_DEMAND_WEIGHT = 100


class P9DailyDemandConstraint(BaseConstraint):
    priority = "P9"
    group = "demand"

    def compile(self, ctx: SolverContext) -> list[ConstraintSpec]:
        specs: list[ConstraintSpec] = []
        for d in range(ctx.num_days):
            dd = ctx.get_daily_demand(ctx.day_dates[d])
            if dd is None:
                continue

            var_keys: list[str] = []
            for m in range(ctx.num_members):
                for k in ctx.available_patterns(m):
                    var_keys.append(ctx.x_key(m, d, k))
            coefficients = [1] * len(var_keys)

            specs.append(LinearConstraint(
                var_keys=var_keys,
                coefficients=coefficients,
                lb=dd.min_total,
                ub=dd.max_total,
                is_hard=False,
                penalty_weight=DEFAULT_DEMAND_WEIGHT,
                name=f"P9_demand_{d}",
            ))
        return specs
