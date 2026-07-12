from __future__ import annotations

import json
import time
from datetime import date, time as dtime
from pathlib import Path

import pytest

from solver_core.engine import solve
from solver_core.models import (
    DailyDemand,
    ForbiddenTransition,
    Member,
    PersonConstraint,
    ShiftPattern,
    SolverConfig,
    SolverInput,
)


def _generate_input(num_members: int, num_days: int = 31, time_limit: int = 120) -> SolverInput:
    patterns = [
        ShiftPattern(id="A", name="Day A", start_time=dtime(8, 0), end_time=dtime(16, 0), work_hours=7.5),
        ShiftPattern(id="B", name="Day B", start_time=dtime(9, 0), end_time=dtime(17, 0), work_hours=7.5),
        ShiftPattern(id="C", name="Late", start_time=dtime(14, 0), end_time=dtime(22, 0), work_hours=7.5),
        ShiftPattern(id="N", name="Night", start_time=dtime(22, 0), end_time=dtime(6, 0), work_hours=7.5),
        ShiftPattern(id="S", name="Short", start_time=dtime(10, 0), end_time=dtime(15, 0), work_hours=4.5),
    ]
    members = [Member(id=f"m{i:02d}", name=f"Staff_{i:02d}") for i in range(1, num_members + 1)]
    person_constraints = [
        PersonConstraint(
            member_id=f"m{i:02d}",
            period_work_days_min=num_days - 12,
            period_work_days_max=num_days - 8,
            max_consecutive_work_days=5,
            max_consecutive_rest_days=3,
        )
        for i in range(1, num_members + 1)
    ]
    forbidden_transitions = [
        ForbiddenTransition(from_pattern_id="N", to_pattern_id="A"),
        ForbiddenTransition(from_pattern_id="N", to_pattern_id="B"),
    ]
    min_per_day = max(2, num_members * 2 // 5)
    max_per_day = min(num_members, num_members * 4 // 5)
    start = date(2026, 7, 1)
    daily_demands = [
        DailyDemand(
            date=date(2026, 7, d + 1),
            min_total=min_per_day,
            max_total=max_per_day,
        )
        for d in range(num_days)
    ]

    return SolverInput(
        start_date=start,
        num_days=num_days,
        patterns=patterns,
        members=members,
        person_constraints=person_constraints,
        forbidden_transitions=forbidden_transitions,
        daily_demands=daily_demands,
        config=SolverConfig(time_limit_seconds=time_limit),
    )


class TestPerformance:

    def test_10_members_under_10s(self):
        inp = _generate_input(10, time_limit=30)
        start = time.time()
        output = solve(inp)
        elapsed = time.time() - start

        assert output.status in ("optimal", "feasible")
        assert elapsed < 10, f"10 members took {elapsed:.1f}s (target: <10s)"
        print(f"\n  10 members: {elapsed:.1f}s, penalty={output.total_penalty}, score={output.health_score}")

    def test_20_members_under_30s(self):
        inp = _generate_input(20, time_limit=60)
        start = time.time()
        output = solve(inp)
        elapsed = time.time() - start

        assert output.status in ("optimal", "feasible")
        assert elapsed < 30, f"20 members took {elapsed:.1f}s (target: <30s)"
        print(f"\n  20 members: {elapsed:.1f}s, penalty={output.total_penalty}, score={output.health_score}")

    def test_50_members_under_120s(self):
        inp = _generate_input(50, time_limit=120)
        start = time.time()
        output = solve(inp)
        elapsed = time.time() - start

        assert output.status in ("optimal", "feasible")
        assert elapsed < 120, f"50 members took {elapsed:.1f}s (target: <120s)"
        print(f"\n  50 members: {elapsed:.1f}s, penalty={output.total_penalty}, score={output.health_score}")

    def test_100_members_under_300s(self):
        inp = _generate_input(100, time_limit=240)
        start = time.time()
        output = solve(inp)
        elapsed = time.time() - start

        assert output.status in ("optimal", "feasible")
        assert elapsed < 300, f"100 members took {elapsed:.1f}s (target: <300s)"
        assert len(output.assignments) == 100 * 31
        print(f"\n  100 members: {elapsed:.1f}s, penalty={output.total_penalty}, score={output.health_score}")
