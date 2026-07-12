from __future__ import annotations

from ..context import SolverContext
from .base import BaseConstraint, ConstraintSpec, LinearConstraint, WindowMax

DEFAULT_WEIGHT = 30


class P7ConsecutiveRestConstraint(BaseConstraint):
    priority = "P7"
    group = "personal"

    def compile(self, ctx: SolverContext) -> list[ConstraintSpec]:
        specs: list[ConstraintSpec] = []

        for m in range(ctx.num_members):
            pc = ctx.get_person_constraint(ctx.input.members[m].id)
            if pc is None or pc.max_consecutive_rest_days is None:
                continue
            max_cr = pc.max_consecutive_rest_days

            var_keys_per_pos: list[list[str]] = []
            for d in range(ctx.num_days):
                var_keys_per_pos.append([ctx.rest_key(m, d)])

            specs.append(WindowMax(
                var_keys_per_position=var_keys_per_pos,
                window_size=max_cr + 1,
                max_value=max_cr,
                is_hard=False,
                penalty_weight=DEFAULT_WEIGHT,
                name=f"P7_consrest_{m}",
            ))

            self._add_carry_over(ctx, m, max_cr, specs)
        return specs

    def _add_carry_over(self, ctx, m, max_cr, specs):
        co = ctx.get_carry_over(ctx.input.members[m].id)
        if co is None or co.trailing_rest_days <= 0:
            return

        trailing = co.trailing_rest_days
        allowed = max_cr - trailing
        if allowed < 0:
            allowed = 0

        boundary_len = min(allowed + 1, ctx.num_days)
        if boundary_len <= 0:
            return

        var_keys = [ctx.rest_key(m, d) for d in range(boundary_len)]

        specs.append(LinearConstraint(
            var_keys=var_keys,
            coefficients=[1] * len(var_keys),
            ub=allowed,
            is_hard=False,
            penalty_weight=DEFAULT_WEIGHT,
            name=f"P7_carry_{m}",
        ))
