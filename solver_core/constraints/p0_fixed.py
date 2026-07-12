from __future__ import annotations

from ..context import SolverContext
from .base import BaseConstraint, ConstraintSpec, FixedVariable


class P0FixedConstraint(BaseConstraint):
    priority = "P0"
    group = "fixed"

    def compile(self, ctx: SolverContext) -> list[ConstraintSpec]:
        specs: list[ConstraintSpec] = []
        for fa in ctx.input.fixed_assignments:
            m = ctx.member_idx(fa.member_id)
            d_date = fa.date
            if d_date not in ctx.day_dates:
                continue
            d = ctx.day_dates.index(d_date)

            if fa.type == "rest":
                specs.append(FixedVariable(
                    var_key=ctx.rest_key(m, d), value=1,
                    name=f"P0_rest_{fa.member_id}_{d_date}",
                ))
            elif fa.type == "work" and fa.pattern_id:
                k = ctx.pattern_idx(fa.pattern_id)
                specs.append(FixedVariable(
                    var_key=ctx.x_key(m, d, k), value=1,
                    name=f"P0_work_{fa.member_id}_{d_date}",
                ))
        return specs
