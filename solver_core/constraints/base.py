from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..context import SolverContext
from ..models import SolverWarning


@dataclass
class ConstraintSpec:
    name: str = ""
    is_hard: bool = True
    penalty_weight: int = 0


@dataclass
class LinearConstraint(ConstraintSpec):
    var_keys: list[str] = field(default_factory=list)
    coefficients: list[int] = field(default_factory=list)
    lb: int | None = None
    ub: int | None = None


@dataclass
class ImplicationConstraint(ConstraintSpec):
    if_var_key: str = ""
    if_val: int = 1
    then_var_key: str = ""
    then_val: int = 1


@dataclass
class FixedVariable(ConstraintSpec):
    var_key: str = ""
    value: int = 0


@dataclass
class ExactlyOne(ConstraintSpec):
    var_keys: list[str] = field(default_factory=list)


@dataclass
class WindowMax(ConstraintSpec):
    var_keys_per_position: list[list[str]] = field(default_factory=list)
    window_size: int = 1
    max_value: int = 0


@dataclass
class MinimizeDiff(ConstraintSpec):
    """Minimize max(counts) - min(counts) for a set of count expressions."""
    count_var_keys: list[list[str]] = field(default_factory=list)
    count_coefficients: list[list[int]] = field(default_factory=list)


class BaseConstraint(ABC):
    priority: str = ""
    group: str = ""
    depends_on: list[str] = []

    @abstractmethod
    def compile(self, ctx: SolverContext) -> list[ConstraintSpec]:
        ...

    def validate(self, ctx: SolverContext) -> list[SolverWarning]:
        return []
