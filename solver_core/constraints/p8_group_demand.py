from __future__ import annotations

from ..context import SolverContext
from ..models import PatternType
from .base import BaseConstraint, ConstraintSpec, LinearConstraint

DEFAULT_WEIGHT = 60


class P8GroupDemandConstraint(BaseConstraint):
    priority = "P8"
    group = "group"

    def compile(self, ctx: SolverContext) -> list[ConstraintSpec]:
        specs: list[ConstraintSpec] = []
        travel_indices = {
            i for i, p in enumerate(ctx.input.patterns)
            if p.type == PatternType.TRAVEL
        }
        work_indices = {
            i for i, p in enumerate(ctx.input.patterns)
            if p.type not in (PatternType.REST, PatternType.HOLIDAY, PatternType.LEAVE, PatternType.TRAVEL)
        }

        for gd in ctx.input.group_demands:
            if gd.date not in ctx.day_dates:
                continue
            d = ctx.day_dates.index(gd.date)
            group_members = ctx.group_member_indices(gd.group_id)
            if not group_members:
                continue

            if gd.pattern_id is None:
                var_keys = []
                for m in group_members:
                    for k in ctx.all_patterns_for_member(m):
                        if k in work_indices:
                            var_keys.append(ctx.x_key(m, d, k))
                if not var_keys:
                    continue
                specs.append(LinearConstraint(
                    var_keys=var_keys,
                    coefficients=[1] * len(var_keys),
                    lb=gd.min_count,
                    is_hard=False,
                    penalty_weight=DEFAULT_WEIGHT,
                    name=f"P8_grp_{gd.group_id}_{d}_any",
                ))
            else:
                if gd.pattern_id not in ctx._pattern_id_to_idx:
                    continue
                k = ctx.pattern_idx(gd.pattern_id)
                if k in travel_indices:
                    continue
                var_keys = [
                    ctx.x_key(m, d, k)
                    for m in group_members
                    if k in ctx.all_patterns_for_member(m)
                ]
                if not var_keys:
                    continue
                specs.append(LinearConstraint(
                    var_keys=var_keys,
                    coefficients=[1] * len(var_keys),
                    lb=gd.min_count,
                    is_hard=False,
                    penalty_weight=DEFAULT_WEIGHT,
                    name=f"P8_grp_{gd.group_id}_{d}_{gd.pattern_id}",
                ))
        return specs
