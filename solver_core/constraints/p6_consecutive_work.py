from __future__ import annotations

from ..context import SolverContext
from .base import BaseConstraint, ConstraintSpec, LinearConstraint, WindowMax

DEFAULT_WEIGHT = 80


class P6ConsecutiveWorkConstraint(BaseConstraint):
    priority = "P6"
    group = "personal"

    def compile(self, ctx: SolverContext) -> list[ConstraintSpec]:
        specs: list[ConstraintSpec] = []

        for m in range(ctx.num_members):
            pc = ctx.get_person_constraint(ctx.input.members[m].id)
            if pc is None or pc.max_consecutive_work_days is None:
                continue
            max_cw = pc.max_consecutive_work_days

            var_keys_per_pos: list[list[str]] = []
            for d in range(ctx.num_days):
                day_vars = [ctx.x_key(m, d, k) for k in ctx.available_patterns(m)]
                var_keys_per_pos.append(day_vars)

            specs.append(WindowMax(
                var_keys_per_position=var_keys_per_pos,
                window_size=max_cw + 1,
                max_value=max_cw,
                is_hard=False,
                penalty_weight=DEFAULT_WEIGHT,
                name=f"P6_conswork_{m}",
            ))

            self._add_carry_over(ctx, m, max_cw, specs)
        return specs

    def _add_carry_over(self, ctx, m, max_cw, specs):
        co = ctx.get_carry_over(ctx.input.members[m].id)
        if co is None or co.trailing_work_days <= 0:
            return

        trailing = co.trailing_work_days
        allowed = max_cw - trailing
        if allowed < 0:
            allowed = 0

        boundary_len = min(allowed + 1, ctx.num_days)
        if boundary_len <= 0:
            return

        var_keys: list[str] = []
        for d in range(boundary_len):
            for k in ctx.available_patterns(m):
                var_keys.append(ctx.x_key(m, d, k))

        specs.append(LinearConstraint(
            var_keys=var_keys,
            coefficients=[1] * len(var_keys),
            ub=allowed,
            is_hard=False,
            penalty_weight=DEFAULT_WEIGHT,
            name=f"P6_carry_{m}",
        ))
