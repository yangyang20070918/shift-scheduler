from __future__ import annotations

from datetime import date, time as dtime

import pytest

from solver_core.engine import solve
from solver_core.models import (
    DailyDemand,
    FixedAssignment,
    Member,
    PersonConstraint,
    ShiftPattern,
    SolverConfig,
    SolverInput,
)
from solver_core.scenario import ScenarioComparator, BALANCED, STAFFING_PRIORITY, PERSONAL_PRIORITY


@pytest.fixture
def constrained_input() -> SolverInput:
    patterns = [
        ShiftPattern(id="A", name="Day A", start_time=dtime(8, 0), end_time=dtime(16, 0), work_hours=7.5),
        ShiftPattern(id="B", name="Day B", start_time=dtime(9, 0), end_time=dtime(17, 0), work_hours=7.5),
        ShiftPattern(id="N", name="Night", start_time=dtime(22, 0), end_time=dtime(6, 0), work_hours=7.5),
    ]
    members = [Member(id=f"m{i}", name=f"Member{i}") for i in range(1, 6)]
    person_constraints = [
        PersonConstraint(
            member_id=f"m{i}",
            period_work_days_min=12,
            period_work_days_max=16,
            max_consecutive_work_days=4,
            max_consecutive_rest_days=2,
        )
        for i in range(1, 6)
    ]
    daily_demands = [
        DailyDemand(date=date(2026, 7, d + 1), min_total=3, max_total=4)
        for d in range(20)
    ]
    fixed_assignments = [
        FixedAssignment(member_id="m1", date=date(2026, 7, 1), type="rest"),
        FixedAssignment(member_id="m1", date=date(2026, 7, 2), type="rest"),
        FixedAssignment(member_id="m1", date=date(2026, 7, 3), type="rest"),
    ]

    return SolverInput(
        start_date=date(2026, 7, 1),
        num_days=20,
        patterns=patterns,
        members=members,
        person_constraints=person_constraints,
        daily_demands=daily_demands,
        fixed_assignments=fixed_assignments,
        config=SolverConfig(time_limit_seconds=15),
    )


class TestExplainEngine:

    def test_violations_have_factors(self, constrained_input: SolverInput):
        output = solve(constrained_input)

        if output.violations:
            has_factors = any(v.contributing_factors for v in output.violations)
            has_suggestions = any(v.suggestions for v in output.violations)
            assert has_factors or has_suggestions, "Violations should have explanations"

    def test_explain_demand_violation(self):
        patterns = [
            ShiftPattern(id="A", name="Day", start_time=dtime(9, 0), end_time=dtime(17, 0), work_hours=8.0),
        ]
        members = [
            Member(id="m1", name="Alice"),
            Member(id="m2", name="Bob"),
            Member(id="m3", name="Charlie"),
        ]
        daily_demands = [
            DailyDemand(date=date(2026, 7, 1), min_total=2, max_total=3),
        ]
        fixed_assignments = [
            FixedAssignment(member_id="m1", date=date(2026, 7, 1), type="rest"),
            FixedAssignment(member_id="m2", date=date(2026, 7, 1), type="rest"),
            FixedAssignment(member_id="m3", date=date(2026, 7, 1), type="rest"),
        ]
        inp = SolverInput(
            start_date=date(2026, 7, 1), num_days=1,
            patterns=patterns, members=members,
            daily_demands=daily_demands,
            fixed_assignments=fixed_assignments,
            config=SolverConfig(time_limit_seconds=5),
        )
        output = solve(inp)

        demand_violations = [v for v in output.violations if v.priority == "P9"]
        assert len(demand_violations) > 0
        v = demand_violations[0]
        assert v.contributing_factors
        assert any("固定休息" in f for f in v.contributing_factors)
        assert v.suggestions


class TestScenarioComparison:

    def test_three_scenarios(self, constrained_input: SolverInput):
        comparator = ScenarioComparator()
        comparison = comparator.compare(constrained_input)

        assert len(comparison.scenarios) == 3
        names = [s.profile.name for s in comparison.scenarios]
        assert "balanced" in names
        assert "staffing_priority" in names
        assert "personal_priority" in names

    def test_all_scenarios_produce_results(self, constrained_input: SolverInput):
        comparator = ScenarioComparator()
        comparison = comparator.compare(constrained_input)

        for s in comparison.scenarios:
            assert s.output.status in ("optimal", "feasible")
            assert len(s.output.assignments) == 5 * 20

    def test_summary_structure(self, constrained_input: SolverInput):
        comparator = ScenarioComparator()
        comparison = comparator.compare(constrained_input)
        summary = comparison.summary()

        assert "balanced" in summary
        assert "staffing_priority" in summary
        assert "personal_priority" in summary
        for name, data in summary.items():
            assert "health_score" in data
            assert "total_penalty" in data
            assert 0 <= data["health_score"] <= 100
