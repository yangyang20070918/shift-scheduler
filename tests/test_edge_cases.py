from __future__ import annotations

from datetime import date, time as dtime

import pytest

from solver_core.engine import solve
from solver_core.models import (
    DailyDemand,
    FixedAssignment,
    ForbiddenTransition,
    Member,
    PatternChain,
    ChainNode,
    PeriodCarryOver,
    PersonConstraint,
    ShiftPattern,
    SolverConfig,
    SolverInput,
)


@pytest.fixture
def base_patterns():
    return [
        ShiftPattern(id="A", name="Day", start_time=dtime(9, 0), end_time=dtime(17, 0), work_hours=8.0),
        ShiftPattern(id="N", name="Night", start_time=dtime(22, 0), end_time=dtime(6, 0), work_hours=8.0),
    ]


class TestEdgeCases:

    def test_all_fixed_rest(self, base_patterns):
        members = [Member(id=f"m{i}", name=f"M{i}") for i in range(1, 4)]
        fixed = [
            FixedAssignment(member_id=f"m{i}", date=date(2026, 7, d + 1), type="rest")
            for i in range(1, 4) for d in range(7)
        ]
        inp = SolverInput(
            start_date=date(2026, 7, 1), num_days=7,
            patterns=base_patterns, members=members,
            fixed_assignments=fixed,
            config=SolverConfig(time_limit_seconds=5),
        )
        output = solve(inp)
        assert output.status in ("optimal", "feasible")
        assert all(a.is_rest for a in output.assignments)

    def test_single_day_period(self, base_patterns):
        members = [Member(id="m1", name="Alice")]
        inp = SolverInput(
            start_date=date(2026, 7, 1), num_days=1,
            patterns=base_patterns, members=members,
            config=SolverConfig(time_limit_seconds=5),
        )
        output = solve(inp)
        assert output.status in ("optimal", "feasible")
        assert len(output.assignments) == 1

    def test_demand_exceeds_available(self, base_patterns):
        members = [Member(id=f"m{i}", name=f"M{i}") for i in range(1, 4)]
        daily_demands = [
            DailyDemand(date=date(2026, 7, 1), min_total=2, max_total=3),
        ]
        fixed = [
            FixedAssignment(member_id="m1", date=date(2026, 7, 1), type="rest"),
            FixedAssignment(member_id="m2", date=date(2026, 7, 1), type="rest"),
        ]
        inp = SolverInput(
            start_date=date(2026, 7, 1), num_days=1,
            patterns=base_patterns, members=members,
            daily_demands=daily_demands,
            fixed_assignments=fixed,
            config=SolverConfig(time_limit_seconds=5),
        )
        output = solve(inp)
        assert output.status in ("optimal", "feasible")
        demand_v = [v for v in output.violations if v.priority == "P9"]
        assert len(demand_v) > 0

    def test_carry_over_consecutive(self, base_patterns):
        members = [Member(id="m1", name="Alice")]
        carry_over = [
            PeriodCarryOver(member_id="m1", trailing_work_days=4),
        ]
        person_constraints = [
            PersonConstraint(member_id="m1", max_consecutive_work_days=5),
        ]
        daily_demands = [
            DailyDemand(date=date(2026, 7, d + 1), min_total=1, max_total=1)
            for d in range(7)
        ]
        inp = SolverInput(
            start_date=date(2026, 7, 1), num_days=7,
            patterns=base_patterns, members=members,
            carry_over=carry_over,
            person_constraints=person_constraints,
            daily_demands=daily_demands,
            config=SolverConfig(time_limit_seconds=5),
        )
        output = solve(inp)
        assert output.status in ("optimal", "feasible")
        rest_days = [a for a in output.assignments if a.is_rest]
        assert len(rest_days) >= 1

    def test_forbidden_transition_respected(self, base_patterns):
        members = [Member(id="m1", name="Alice")]
        forbidden = [ForbiddenTransition(from_pattern_id="N", to_pattern_id="A")]
        inp = SolverInput(
            start_date=date(2026, 7, 1), num_days=7,
            patterns=base_patterns, members=members,
            forbidden_transitions=forbidden,
            config=SolverConfig(time_limit_seconds=5),
        )
        output = solve(inp)
        assert output.status in ("optimal", "feasible")
        assigns = sorted(output.assignments, key=lambda a: a.date)
        for i in range(len(assigns) - 1):
            if assigns[i].pattern_id == "N":
                assert assigns[i + 1].pattern_id != "A"

    def test_pattern_chain(self):
        patterns = [
            ShiftPattern(id="A", name="Day", start_time=dtime(9, 0), end_time=dtime(17, 0), work_hours=8.0),
            ShiftPattern(id="N", name="Night", start_time=dtime(22, 0), end_time=dtime(6, 0), work_hours=8.0),
            ShiftPattern(id="R", name="Chain Rest", start_time=dtime(0, 0), end_time=dtime(0, 0),
                         work_hours=0.0, is_companion=True),
        ]
        members = [Member(id="m1", name="Alice")]
        chains = [
            PatternChain(
                id="night_chain", trigger_pattern_id="N", total_length=3,
                nodes=[
                    ChainNode(day_offset=1, is_rest=True),
                    ChainNode(day_offset=2, candidates=["A"], is_rest=False),
                ],
            ),
        ]
        fixed = [
            FixedAssignment(member_id="m1", date=date(2026, 7, 1), type="work", pattern_id="N"),
        ]
        inp = SolverInput(
            start_date=date(2026, 7, 1), num_days=5,
            patterns=patterns, members=members,
            pattern_chains=chains,
            fixed_assignments=fixed,
            config=SolverConfig(time_limit_seconds=5),
        )
        output = solve(inp)
        assert output.status in ("optimal", "feasible")
        assigns = sorted(output.assignments, key=lambda a: a.date)
        assert assigns[0].pattern_id == "N"
        assert assigns[1].is_rest is True
        assert assigns[2].pattern_id == "A"

    def test_contradicting_constraints(self, base_patterns):
        members = [Member(id="m1", name="Alice")]
        person_constraints = [
            PersonConstraint(member_id="m1", period_work_days_min=7, max_consecutive_work_days=2),
        ]
        inp = SolverInput(
            start_date=date(2026, 7, 1), num_days=7,
            patterns=base_patterns, members=members,
            person_constraints=person_constraints,
            config=SolverConfig(time_limit_seconds=5),
        )
        output = solve(inp)
        assert output.status in ("optimal", "feasible")
        assert output.violations
