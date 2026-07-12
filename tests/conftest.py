from __future__ import annotations

import json
from datetime import date, time
from pathlib import Path

import pytest

from solver_core.models import (
    DailyDemand,
    FixedAssignment,
    Member,
    PatternType,
    PersonConstraint,
    ShiftPattern,
    SolverConfig,
    SolverInput,
)

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def basic_10_input() -> SolverInput:
    with open(DATA_DIR / "basic_10.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return SolverInput.model_validate(data)


@pytest.fixture
def minimal_input() -> SolverInput:
    patterns = [
        ShiftPattern(
            id="day", name="Day", start_time=time(9, 0),
            end_time=time(17, 0), work_hours=8.0,
        ),
        ShiftPattern(
            id="night", name="Night", start_time=time(22, 0),
            end_time=time(6, 0), work_hours=8.0,
        ),
    ]
    members = [
        Member(id="m1", name="Alice"),
        Member(id="m2", name="Bob"),
        Member(id="m3", name="Charlie"),
    ]
    return SolverInput(
        start_date=date(2026, 7, 1),
        num_days=7,
        patterns=patterns,
        members=members,
        config=SolverConfig(time_limit_seconds=10),
    )
