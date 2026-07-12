from __future__ import annotations

from ..context import SolverContext
from .base import BaseConstraint, ConstraintSpec, FixedVariable, ImplicationConstraint


class P1AForbiddenConstraint(BaseConstraint):
    priority = "P1-A"
    group = "pattern"

    def compile(self, ctx: SolverContext) -> list[ConstraintSpec]:
        specs: list[ConstraintSpec] = []
        for ft in ctx.input.forbidden_transitions:
            from_k = ctx.pattern_idx(ft.from_pattern_id)
            to_k = ctx.pattern_idx(ft.to_pattern_id)

            for m in range(ctx.num_members):
                avail = ctx.all_patterns_for_member(m)
                if from_k not in avail or to_k not in avail:
                    continue

                for d in range(ctx.num_days - 1):
                    specs.append(ImplicationConstraint(
                        if_var_key=ctx.x_key(m, d, from_k),
                        if_val=1,
                        then_var_key=ctx.x_key(m, d + 1, to_k),
                        then_val=0,
                        name=f"P1A_{m}_{d}_{from_k}_{to_k}",
                    ))

        self._add_carry_over(ctx, specs)
        return specs

    def _add_carry_over(self, ctx: SolverContext, specs: list[ConstraintSpec]):
        for m in range(ctx.num_members):
            co = ctx.get_carry_over(ctx.input.members[m].id)
            if co is None or co.last_day_pattern_id is None:
                continue
            last_pid = co.last_day_pattern_id
            if last_pid not in ctx._pattern_id_to_idx:
                continue
            from_k = ctx.pattern_idx(last_pid)

            for ft in ctx.input.forbidden_transitions:
                if ctx.pattern_idx(ft.from_pattern_id) != from_k:
                    continue
                to_k = ctx.pattern_idx(ft.to_pattern_id)
                if to_k in ctx.all_patterns_for_member(m):
                    specs.append(FixedVariable(
                        var_key=ctx.x_key(m, 0, to_k), value=0,
                        name=f"P1A_carry_{m}_{to_k}",
                    ))
