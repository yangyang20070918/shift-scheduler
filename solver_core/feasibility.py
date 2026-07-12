from __future__ import annotations

from .context import SolverContext
from .models import SolverWarning


class FeasibilityChecker:

    def check(self, ctx: SolverContext) -> list[SolverWarning]:
        warnings: list[SolverWarning] = []
        self._check_member_patterns(ctx, warnings)
        self._check_demand_vs_supply(ctx, warnings)
        self._check_fixed_conflicts(ctx, warnings)
        return warnings

    def _check_member_patterns(self, ctx: SolverContext, warnings: list[SolverWarning]):
        for m in range(ctx.num_members):
            avail = ctx.available_patterns(m)
            if not avail:
                warnings.append(SolverWarning(
                    warning_type="pre_solve",
                    severity="error",
                    target=ctx.input.members[m].id,
                    message=f"Member '{ctx.input.members[m].name}' has no available patterns (only rest).",
                ))

    def _check_demand_vs_supply(self, ctx: SolverContext, warnings: list[SolverWarning]):
        for d in range(ctx.num_days):
            dd = ctx.get_daily_demand(ctx.day_dates[d])
            if dd is None:
                continue
            if dd.min_total > ctx.num_members:
                warnings.append(SolverWarning(
                    warning_type="pre_solve",
                    severity="error",
                    target=str(ctx.day_dates[d]),
                    message=f"Daily demand min ({dd.min_total}) exceeds total members ({ctx.num_members}) on {ctx.day_dates[d]}.",
                ))

    def _check_fixed_conflicts(self, ctx: SolverContext, warnings: list[SolverWarning]):
        for fa in ctx.input.fixed_assignments:
            if fa.date not in ctx.day_dates:
                continue
            if fa.type == "work" and fa.pattern_id:
                if fa.pattern_id not in ctx._pattern_id_to_idx:
                    warnings.append(SolverWarning(
                        warning_type="pre_solve",
                        severity="warning",
                        target=fa.member_id,
                        message=f"Fixed assignment references unknown pattern '{fa.pattern_id}'.",
                    ))
                else:
                    m = ctx.member_idx(fa.member_id)
                    k = ctx.pattern_idx(fa.pattern_id)
                    if k not in ctx.all_patterns_for_member(m):
                        warnings.append(SolverWarning(
                            warning_type="pre_solve",
                            severity="warning",
                            target=fa.member_id,
                            message=f"Fixed pattern '{fa.pattern_id}' not available for member '{fa.member_id}'.",
                        ))
