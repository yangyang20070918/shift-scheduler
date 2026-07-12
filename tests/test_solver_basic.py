from __future__ import annotations

from datetime import date

import pytest

from solver_core.engine import solve
from solver_core.models import SolverInput, SolverOutput


class TestEndToEnd:

    def test_basic_10_produces_assignments(self, basic_10_input: SolverInput):
        output = solve(basic_10_input)

        assert output.status in ("optimal", "feasible")
        assert output.solve_time_seconds < 30
        assert len(output.assignments) == 10 * 31

    def test_basic_10_p0_fixed_respected(self, basic_10_input: SolverInput):
        output = solve(basic_10_input)

        m01_jul5 = [
            a for a in output.assignments
            if a.member_id == "m01" and a.date == date(2026, 7, 5)
        ]
        assert len(m01_jul5) == 1
        assert m01_jul5[0].is_rest is True

        m02_jul12 = [
            a for a in output.assignments
            if a.member_id == "m02" and a.date == date(2026, 7, 12)
        ]
        assert len(m02_jul12) == 1
        assert m02_jul12[0].is_rest is True

    def test_basic_10_health_score(self, basic_10_input: SolverInput):
        output = solve(basic_10_input)

        assert 0.0 <= output.health_score <= 100.0
        assert output.score_breakdown is not None

    def test_basic_10_forbidden_transition(self, basic_10_input: SolverInput):
        output = solve(basic_10_input)

        by_member: dict[str, list] = {}
        for a in output.assignments:
            by_member.setdefault(a.member_id, []).append(a)

        for mid, assigns in by_member.items():
            assigns.sort(key=lambda a: a.date)
            for i in range(len(assigns) - 1):
                curr = assigns[i]
                nxt = assigns[i + 1]
                if curr.pattern_id == "N":
                    assert nxt.pattern_id not in ("A", "B"), (
                        f"{mid}: N→{nxt.pattern_id} on {nxt.date}"
                    )

    def test_basic_10_period_days(self, basic_10_input: SolverInput):
        output = solve(basic_10_input)

        by_member: dict[str, int] = {}
        for a in output.assignments:
            if not a.is_rest:
                by_member[a.member_id] = by_member.get(a.member_id, 0) + 1

        for mid, days in by_member.items():
            assert 18 <= days <= 25, f"{mid}: {days} work days outside reasonable range"


class TestMinimal:

    def test_minimal_3_members(self, minimal_input: SolverInput):
        output = solve(minimal_input)

        assert output.status in ("optimal", "feasible")
        assert len(output.assignments) == 3 * 7

    def test_empty_demands(self, minimal_input: SolverInput):
        output = solve(minimal_input)
        assert output.health_score == 100.0 or output.total_penalty == 0


class TestInfeasible:

    def test_impossible_demand(self, minimal_input: SolverInput):
        from solver_core.models import DailyDemand

        minimal_input.daily_demands = [
            DailyDemand(date=date(2026, 7, 1), min_total=100, max_total=200),
        ]
        output = solve(minimal_input)
        assert output.warnings
        assert any(w.severity == "error" for w in output.warnings)
