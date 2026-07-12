from __future__ import annotations

from .constraints.base import BaseConstraint, ConstraintSpec
from .context import SolverContext
from .models import SolverWarning


class ConstraintManager:

    def __init__(self):
        self._constraints: list[BaseConstraint] = []
        self._weight_overrides: dict[str, int] = {}

    def register(self, constraint: BaseConstraint):
        self._constraints.append(constraint)

    def register_all_defaults(self):
        from .constraints import ALL_CONSTRAINTS
        for cls in ALL_CONSTRAINTS:
            self._constraints.append(cls())

    def apply_weights(self, profile):
        priority_to_attr = {
            "P2": "p2_weight", "P3": "p3_weight",
            "P4": "p4_weight", "P5": "p5_weight",
            "P6": "p6_weight", "P7": "p7_weight",
            "P8": "p8_weight", "P9": "p9_weight",
            "P10": "p10_weight",
        }
        for priority, attr in priority_to_attr.items():
            if hasattr(profile, attr):
                self._weight_overrides[priority] = getattr(profile, attr)

    def validate_all(self, ctx: SolverContext) -> list[SolverWarning]:
        warnings: list[SolverWarning] = []
        for c in self._sorted():
            warnings.extend(c.validate(ctx))
        return warnings

    def compile_all(self, ctx: SolverContext) -> list[ConstraintSpec]:
        specs: list[ConstraintSpec] = []
        for c in self._sorted():
            constraint_specs = c.compile(ctx)
            if c.priority in self._weight_overrides:
                weight = self._weight_overrides[c.priority]
                for s in constraint_specs:
                    if not s.is_hard and s.penalty_weight > 0:
                        s.penalty_weight = weight
            specs.extend(constraint_specs)
        return specs

    def _sorted(self) -> list[BaseConstraint]:
        priority_order = {
            "P0": 0, "P1-A": 1, "P1-B": 2,
            "P2": 3, "P3": 4, "P4": 5, "P5": 6,
            "P6": 7, "P7": 8, "P8": 9, "P9": 10, "P10": 11,
        }
        return sorted(
            self._constraints,
            key=lambda c: priority_order.get(c.priority, 99),
        )
