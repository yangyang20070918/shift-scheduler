from __future__ import annotations

from ..context import SolverContext
from ..models import PatternType
from .base import BaseConstraint, ConstraintSpec, LinearConstraint

DEFAULT_DEMAND_WEIGHT = 100


class P9DailyDemandConstraint(BaseConstraint):
    priority = "P9"
    group = "demand"

    def compile(self, ctx: SolverContext) -> list[ConstraintSpec]:
        specs: list[ConstraintSpec] = []
        travel_indices = {
            i for i, p in enumerate(ctx.input.patterns)
            if p.type == PatternType.TRAVEL
        }
        for d in range(ctx.num_days):
            dd = ctx.get_daily_demand(ctx.day_dates[d])
            if dd is None:
                continue

            var_keys: list[str] = []
            for m in range(ctx.num_members):
                for k in ctx.available_patterns(m):
                    if k not in travel_indices:
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

        pd_by_date: dict[int, list] = {}
        for pd in ctx.input.pattern_demands:
            if pd.date in ctx.day_dates:
                d = ctx.day_dates.index(pd.date)
                pd_by_date.setdefault(d, []).append(pd)

        for d, pds in pd_by_date.items():
            for pd in pds:
                if pd.pattern_id not in ctx._pattern_id_to_idx:
                    continue
                k = ctx.pattern_idx(pd.pattern_id)
                if k in travel_indices:
                    continue
                var_keys = [
                    ctx.x_key(m, d, k)
                    for m in range(ctx.num_members)
                    if k in ctx.available_patterns(m)
                ]
                if not var_keys:
                    continue
                specs.append(LinearConstraint(
                    var_keys=var_keys,
                    coefficients=[1] * len(var_keys),
                    lb=pd.min_count,
                    is_hard=False,
                    penalty_weight=DEFAULT_DEMAND_WEIGHT,
                    name=f"P9_pattern_{pd.pattern_id}_{d}",
                ))

        return specs
