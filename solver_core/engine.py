from __future__ import annotations

import json
import sys

from .analyzer import ViolationAnalyzer
from .compiler import CPSATCompiler
from .context import SolverContext
from .explain import ExplainEngine
from .feasibility import FeasibilityChecker
from .manager import ConstraintManager
from .models import SolverInput, SolverOutput
from .scoring import compute_health_score
from .solver import MultiStageSolver


def solve(input_data: dict | str | SolverInput) -> SolverOutput:
    if isinstance(input_data, str):
        input_data = json.loads(input_data)
    if isinstance(input_data, dict):
        inp = SolverInput.model_validate(input_data)
    else:
        inp = input_data

    return _solve_core(inp)


def solve_with_weights(inp: SolverInput, profile) -> SolverOutput:
    return _solve_core(inp, weight_profile=profile)


def _solve_core(inp: SolverInput, weight_profile=None) -> SolverOutput:
    ctx = SolverContext(inp)

    checker = FeasibilityChecker()
    pre_warnings = checker.check(ctx)

    has_error = any(w.severity == "error" for w in pre_warnings)
    if has_error:
        return SolverOutput(
            status="infeasible",
            warnings=pre_warnings,
        )

    manager = ConstraintManager()
    manager.register_all_defaults()
    validation_warnings = manager.validate_all(ctx)
    pre_warnings.extend(validation_warnings)

    if weight_profile is not None:
        manager.apply_weights(weight_profile)

    specs = manager.compile_all(ctx)

    compiler = CPSATCompiler(ctx)
    solver = MultiStageSolver(ctx, compiler)
    output = solver.solve(specs)

    if output.assignments:
        analyzer = ViolationAnalyzer()
        output.violations = analyzer.analyze(ctx, output.assignments)

        explainer = ExplainEngine()
        output.violations = explainer.explain(ctx, output.assignments, output.violations)

    score, breakdown = compute_health_score(output)
    output.health_score = score
    output.score_breakdown = breakdown
    output.warnings = pre_warnings

    return output


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m solver_core.engine <input.json>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)

    result = solve(data)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
