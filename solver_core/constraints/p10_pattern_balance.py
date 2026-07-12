from __future__ import annotations

from ..context import SolverContext
from .base import BaseConstraint, ConstraintSpec, MinimizeDiff

DEFAULT_WEIGHT = 10


class P10PatternBalanceConstraint(BaseConstraint):
    priority = "P10"
    group = "group"

    def compile(self, ctx: SolverContext) -> list[ConstraintSpec]:
        specs: list[ConstraintSpec] = []
        non_companion = [
            k for k in range(ctx.num_patterns)
            if not ctx.input.patterns[k].is_companion
        ]

        for k in non_companion:
            count_keys: list[list[str]] = []
            count_coeffs: list[list[int]] = []
            has_member = False

            for m in range(ctx.num_members):
                if k not in ctx.available_patterns(m):
                    continue
                has_member = True
                keys = [ctx.x_key(m, d, k) for d in range(ctx.num_days)]
                count_keys.append(keys)
                count_coeffs.append([1] * len(keys))

            if not has_member or len(count_keys) < 2:
                continue

            specs.append(MinimizeDiff(
                count_var_keys=count_keys,
                count_coefficients=count_coeffs,
                penalty_weight=DEFAULT_WEIGHT,
                name=f"P10_bal_{k}",
            ))
        return specs
