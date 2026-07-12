from __future__ import annotations

from ..context import SolverContext
from .base import BaseConstraint, ConstraintSpec, FixedVariable, ImplicationConstraint


class P1BChainConstraint(BaseConstraint):
    priority = "P1-B"
    group = "pattern"
    depends_on = ["P0"]

    def compile(self, ctx: SolverContext) -> list[ConstraintSpec]:
        specs: list[ConstraintSpec] = []
        for chain in ctx.input.pattern_chains:
            trigger_k = ctx.pattern_idx(chain.trigger_pattern_id)

            for m in range(ctx.num_members):
                if trigger_k not in ctx.all_patterns_for_member(m):
                    continue
                self._compile_for_member(ctx, chain, trigger_k, m, specs)

        self._add_carry_over(ctx, specs)
        return specs

    def _compile_for_member(
        self, ctx: SolverContext, chain, trigger_k: int, m: int,
        specs: list[ConstraintSpec],
    ):
        for d in range(ctx.num_days):
            for node in chain.nodes:
                target_d = d + node.day_offset
                if target_d < 0 or target_d >= ctx.num_days:
                    continue
                self._add_node_implications(
                    ctx, m, d, target_d, trigger_k, node, specs,
                )

    def _add_node_implications(
        self, ctx, m, d, target_d, trigger_k, node, specs,
    ):
        trigger_key = ctx.x_key(m, d, trigger_k)

        if node.is_rest:
            specs.append(ImplicationConstraint(
                if_var_key=trigger_key, if_val=1,
                then_var_key=ctx.rest_key(m, target_d), then_val=1,
                name=f"P1B_rest_{m}_{d}_{target_d}",
            ))
            return

        avail = ctx.all_patterns_for_member(m)
        candidate_ks = {
            ctx.pattern_idx(pid)
            for pid in node.candidates
            if pid in ctx._pattern_id_to_idx
        }

        specs.append(ImplicationConstraint(
            if_var_key=trigger_key, if_val=1,
            then_var_key=ctx.rest_key(m, target_d), then_val=0,
            name=f"P1B_norest_{m}_{d}_{target_d}",
        ))

        for k in avail:
            if k not in candidate_ks:
                specs.append(ImplicationConstraint(
                    if_var_key=trigger_key, if_val=1,
                    then_var_key=ctx.x_key(m, target_d, k), then_val=0,
                    name=f"P1B_forbid_{m}_{d}_{target_d}_{k}",
                ))

    def _add_carry_over(self, ctx: SolverContext, specs: list[ConstraintSpec]):
        for m in range(ctx.num_members):
            co = ctx.get_carry_over(ctx.input.members[m].id)
            if co is None or not co.last_n_days_patterns:
                continue

            for chain in ctx.input.pattern_chains:
                trigger_pid = chain.trigger_pattern_id
                for i, prev_pid in enumerate(co.last_n_days_patterns):
                    if prev_pid != trigger_pid:
                        continue
                    days_ago = len(co.last_n_days_patterns) - i
                    for node in chain.nodes:
                        target_d = node.day_offset - days_ago
                        if target_d < 0 or target_d >= ctx.num_days:
                            continue
                        if node.is_rest:
                            specs.append(FixedVariable(
                                var_key=ctx.rest_key(m, target_d), value=1,
                                name=f"P1B_carry_rest_{m}_{target_d}",
                            ))
                        else:
                            candidate_ks = {
                                ctx.pattern_idx(pid)
                                for pid in node.candidates
                                if pid in ctx._pattern_id_to_idx
                            }
                            avail = ctx.all_patterns_for_member(m)
                            specs.append(FixedVariable(
                                var_key=ctx.rest_key(m, target_d), value=0,
                                name=f"P1B_carry_norest_{m}_{target_d}",
                            ))
                            for k in avail:
                                if k not in candidate_ks:
                                    specs.append(FixedVariable(
                                        var_key=ctx.x_key(m, target_d, k), value=0,
                                        name=f"P1B_carry_forbid_{m}_{target_d}_{k}",
                                    ))
