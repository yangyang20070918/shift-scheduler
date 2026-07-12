from __future__ import annotations

from ortools.sat.python import cp_model

from .constraints.base import (
    ConstraintSpec,
    ExactlyOne,
    FixedVariable,
    ImplicationConstraint,
    LinearConstraint,
    MinimizeDiff,
    WindowMax,
)
from .context import SolverContext


class CPSATCompiler:

    def __init__(self, ctx: SolverContext):
        self.ctx = ctx
        self.model = cp_model.CpModel()
        self.variables: dict[str, cp_model.IntVar] = {}
        self.penalty_vars: list[cp_model.IntVar] = []
        self.penalty_weights: list[int] = []
        self.balance_vars: list[cp_model.IntVar] = []
        self.balance_weights: list[int] = []
        self._create_variables()

    def _create_variables(self):
        ctx = self.ctx
        for m in range(ctx.num_members):
            assignable = ctx.all_patterns_for_member(m)
            for d in range(ctx.num_days):
                for k in assignable:
                    key = ctx.x_key(m, d, k)
                    self.variables[key] = self.model.new_bool_var(key)

                rest_key = ctx.rest_key(m, d)
                self.variables[rest_key] = self.model.new_bool_var(rest_key)

            self._add_exactly_one_per_day(m)

    def _add_exactly_one_per_day(self, m: int):
        ctx = self.ctx
        assignable = ctx.all_patterns_for_member(m)
        for d in range(ctx.num_days):
            keys = [ctx.x_key(m, d, k) for k in assignable]
            keys.append(ctx.rest_key(m, d))
            vs = [self.variables[k] for k in keys]
            self.model.add_exactly_one(vs)

    def add_specs(self, specs: list[ConstraintSpec]):
        for spec in specs:
            if isinstance(spec, FixedVariable):
                self._add_fixed(spec)
            elif isinstance(spec, ExactlyOne):
                self._add_exactly_one(spec)
            elif isinstance(spec, ImplicationConstraint):
                self._add_implication(spec)
            elif isinstance(spec, LinearConstraint):
                self._add_linear(spec)
            elif isinstance(spec, WindowMax):
                self._add_window_max(spec)
            elif isinstance(spec, MinimizeDiff):
                self._add_minimize_diff(spec)

    def _get_var(self, key: str) -> cp_model.IntVar:
        v = self.variables.get(key)
        if v is None:
            v = self.model.new_bool_var(key)
            self.variables[key] = v
        return v

    def _add_fixed(self, spec: FixedVariable):
        v = self._get_var(spec.var_key)
        self.model.add(v == spec.value)

    def _add_exactly_one(self, spec: ExactlyOne):
        vs = [self._get_var(k) for k in spec.var_keys]
        self.model.add_exactly_one(vs)

    def _add_implication(self, spec: ImplicationConstraint):
        if_var = self._get_var(spec.if_var_key)
        then_var = self._get_var(spec.then_var_key)
        if spec.if_val == 1 and spec.then_val == 1:
            self.model.add_implication(if_var, then_var)
        elif spec.if_val == 1 and spec.then_val == 0:
            self.model.add_implication(if_var, then_var.negated())
        elif spec.if_val == 0 and spec.then_val == 1:
            self.model.add_implication(if_var.negated(), then_var)
        else:
            self.model.add_implication(if_var.negated(), then_var.negated())

    def _add_linear(self, spec: LinearConstraint):
        vs = [self._get_var(k) for k in spec.var_keys]
        if not vs:
            return
        expr = sum(c * v for c, v in zip(spec.coefficients, vs))

        if spec.is_hard:
            if spec.lb is not None:
                self.model.add(expr >= spec.lb)
            if spec.ub is not None:
                self.model.add(expr <= spec.ub)
        else:
            self._add_soft_linear(expr, spec.lb, spec.ub, spec.penalty_weight, spec.name)

    def _add_soft_linear(self, expr, lb, ub, weight, name):
        big_m = self.ctx.num_members * self.ctx.num_days + 1

        if lb is not None:
            shortfall = self.model.new_int_var(0, big_m, f"{name}_short")
            self.model.add(shortfall >= lb - expr)
            self.penalty_vars.append(shortfall)
            self.penalty_weights.append(weight)

        if ub is not None:
            excess = self.model.new_int_var(0, big_m, f"{name}_excess")
            self.model.add(excess >= expr - ub)
            self.penalty_vars.append(excess)
            self.penalty_weights.append(weight)

    def _add_window_max(self, spec: WindowMax):
        positions = spec.var_keys_per_position
        n = len(positions)
        w = spec.window_size

        for start in range(n - w + 1):
            window_vars = []
            for pos in range(start, start + w):
                window_vars.extend(positions[pos])
            vs = [self._get_var(k) for k in window_vars]
            expr = sum(vs)

            if spec.is_hard:
                self.model.add(expr <= spec.max_value)
            else:
                excess = self.model.new_int_var(
                    0, w, f"{spec.name}_win{start}_excess"
                )
                self.model.add(excess >= expr - spec.max_value)
                self.penalty_vars.append(excess)
                self.penalty_weights.append(spec.penalty_weight)

    def _add_minimize_diff(self, spec: MinimizeDiff):
        if len(spec.count_var_keys) < 2:
            return
        count_vars = []
        max_possible = self.ctx.num_days
        for keys, coeffs in zip(spec.count_var_keys, spec.count_coefficients):
            vs = [self._get_var(k) for k in keys]
            cv = self.model.new_int_var(0, max_possible, f"{spec.name}_cnt{len(count_vars)}")
            self.model.add(cv == sum(c * v for c, v in zip(coeffs, vs)))
            count_vars.append(cv)

        max_cnt = self.model.new_int_var(0, max_possible, f"{spec.name}_max")
        min_cnt = self.model.new_int_var(0, max_possible, f"{spec.name}_min")
        self.model.add_max_equality(max_cnt, count_vars)
        self.model.add_min_equality(min_cnt, count_vars)

        diff = self.model.new_int_var(0, max_possible, f"{spec.name}_diff")
        self.model.add(diff == max_cnt - min_cnt)
        self.balance_vars.append(diff)
        self.balance_weights.append(spec.penalty_weight)

    def build_objective(self):
        terms = []
        for pv, pw in zip(self.penalty_vars, self.penalty_weights):
            terms.append(pw * pv)
        for bv, bw in zip(self.balance_vars, self.balance_weights):
            terms.append(bw * bv)
        if terms:
            self.model.minimize(sum(terms))

    def total_penalty_expr(self):
        return sum(pw * pv for pv, pw in zip(self.penalty_vars, self.penalty_weights))
