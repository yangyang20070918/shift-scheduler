from __future__ import annotations

import time

from ortools.sat.python import cp_model

from .compiler import CPSATCompiler
from .constraints.base import ConstraintSpec
from .context import SolverContext
from .models import Assignment, SolverOutput


class MultiStageSolver:

    def __init__(self, ctx: SolverContext, compiler: CPSATCompiler):
        self.ctx = ctx
        self.compiler = compiler
        self.config = ctx.input.config
        self._best_solution: dict[str, int] | None = None
        self._status = cp_model.UNKNOWN
        self._total_wall_time = 0.0

    def solve(self, specs: list[ConstraintSpec]) -> SolverOutput:
        start_time = time.time()
        self.compiler.add_specs(specs)
        self.compiler.build_objective()

        total_limit = self.config.time_limit_seconds
        s1_limit = max(1, int(total_limit * self.config.stage1_ratio))
        s2_limit = max(1, int(total_limit * self.config.stage2_ratio))

        self._solve_stage(s1_limit)

        if self._status == cp_model.FEASIBLE:
            self._solve_stage(s2_limit)

        if self._status == cp_model.FEASIBLE:
            remaining = max(1, total_limit - int(time.time() - start_time))
            if remaining > 1:
                self._solve_stage(remaining)

        self._total_wall_time = time.time() - start_time
        return self._build_output()

    def _solve_stage(self, time_limit: int):
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit
        solver.parameters.num_workers = 8

        if self._best_solution is not None:
            self._apply_hints(solver)

        self._status = solver.solve(self.compiler.model)

        if self._status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
            self._best_solution = {
                key: solver.value(var)
                for key, var in self.compiler.variables.items()
            }

    def _apply_hints(self, solver: cp_model.CpSolver):
        self.compiler.model.clear_hints()
        for key, var in self.compiler.variables.items():
            if key in self._best_solution:
                self.compiler.model.add_hint(var, self._best_solution[key])

    def _build_output(self) -> SolverOutput:
        if self._best_solution is None:
            return SolverOutput(
                status=self._status_str(),
                solve_time_seconds=self._total_wall_time,
            )

        assignments = self._extract_assignments()
        total_penalty = self._compute_penalty()

        return SolverOutput(
            status=self._status_str(),
            solve_time_seconds=round(self._total_wall_time, 3),
            total_penalty=total_penalty,
            assignments=assignments,
        )

    def _extract_assignments(self) -> list[Assignment]:
        ctx = self.ctx
        assignments: list[Assignment] = []

        for m in range(ctx.num_members):
            member = ctx.input.members[m]
            for d in range(ctx.num_days):
                dt = ctx.day_dates[d]
                rest_val = self._best_solution.get(ctx.rest_key(m, d), 0)
                if rest_val == 1:
                    assignments.append(Assignment(
                        member_id=member.id, date=dt, is_rest=True,
                    ))
                    continue

                for k in ctx.all_patterns_for_member(m):
                    key = ctx.x_key(m, d, k)
                    if self._best_solution.get(key, 0) == 1:
                        assignments.append(Assignment(
                            member_id=member.id, date=dt,
                            pattern_id=ctx.input.patterns[k].id,
                        ))
                        break

        return assignments

    def _compute_penalty(self) -> int:
        total = 0
        for pv, pw in zip(self.compiler.penalty_vars, self.compiler.penalty_weights):
            key = pv.name
            val = self._best_solution.get(key, 0)
            total += pw * val
        for bv, bw in zip(self.compiler.balance_vars, self.compiler.balance_weights):
            key = bv.name
            val = self._best_solution.get(key, 0)
            total += bw * val
        return total

    def _status_str(self) -> str:
        return {
            cp_model.OPTIMAL: "optimal",
            cp_model.FEASIBLE: "feasible",
            cp_model.INFEASIBLE: "infeasible",
            cp_model.MODEL_INVALID: "infeasible",
            cp_model.UNKNOWN: "timeout",
        }.get(self._status, "unknown")
