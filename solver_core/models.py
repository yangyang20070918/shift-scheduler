from __future__ import annotations

from datetime import date, time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PatternType(str, Enum):
    NORMAL = "NORMAL"
    REST = "REST"
    LEAVE = "LEAVE"
    TRAINING = "TRAINING"
    MEETING = "MEETING"
    ONCALL = "ONCALL"
    HOLIDAY = "HOLIDAY"
    COMPANION = "COMPANION"
    TRAVEL = "TRAVEL"


class ShiftPattern(BaseModel):
    id: str
    name: str
    type: PatternType = PatternType.NORMAL
    start_time: time
    end_time: time
    break_hours: float = 0.0
    work_hours: float
    is_companion: bool = False
    color_code: str = "#808080"


class Member(BaseModel):
    id: str
    name: str
    available_pattern_ids: list[str] = Field(default_factory=list)


class PersonConstraint(BaseModel):
    member_id: str
    weekly_work_days_min: Optional[int] = None
    weekly_work_days_max: Optional[int] = None
    period_work_days_min: Optional[int] = None
    period_work_days_max: Optional[int] = None
    weekly_work_hours_min: Optional[float] = None
    weekly_work_hours_max: Optional[float] = None
    period_work_hours_min: Optional[float] = None
    period_work_hours_max: Optional[float] = None
    max_consecutive_work_days: Optional[int] = None
    max_consecutive_rest_days: Optional[int] = None


class Group(BaseModel):
    id: str
    name: str
    member_ids: list[str] = Field(default_factory=list)


class ForbiddenTransition(BaseModel):
    from_pattern_id: str
    to_pattern_id: str


class ChainNode(BaseModel):
    day_offset: int
    candidates: list[str] = Field(default_factory=list)
    is_rest: bool = False


class PatternChain(BaseModel):
    id: str
    trigger_pattern_id: str
    nodes: list[ChainNode] = Field(default_factory=list)
    total_length: int = 0


class FixedAssignment(BaseModel):
    member_id: str
    date: date
    type: str  # "work" or "rest"
    pattern_id: Optional[str] = None


class DailyDemand(BaseModel):
    date: date
    min_total: int = 0
    max_total: int = 999


class PatternDemand(BaseModel):
    date: date
    pattern_id: str
    min_count: int = 0


class GroupDemand(BaseModel):
    date: date
    group_id: str
    pattern_id: Optional[str] = None
    min_count: int = 0


class PeriodCarryOver(BaseModel):
    member_id: str
    last_day_pattern_id: Optional[str] = None
    last_n_days_patterns: list[Optional[str]] = Field(default_factory=list)
    trailing_work_days: int = 0
    trailing_rest_days: int = 0
    last_week_work_days: int = 0
    last_week_work_hours: float = 0.0


class SolverConfig(BaseModel):
    time_limit_seconds: int = 120
    week_start_day: int = 1  # 1=Monday, 7=Sunday
    stage1_ratio: float = 0.4
    stage2_ratio: float = 0.4


class SolverInput(BaseModel):
    start_date: date
    num_days: int
    patterns: list[ShiftPattern]
    members: list[Member]
    person_constraints: list[PersonConstraint] = Field(default_factory=list)
    groups: list[Group] = Field(default_factory=list)
    forbidden_transitions: list[ForbiddenTransition] = Field(default_factory=list)
    pattern_chains: list[PatternChain] = Field(default_factory=list)
    fixed_assignments: list[FixedAssignment] = Field(default_factory=list)
    daily_demands: list[DailyDemand] = Field(default_factory=list)
    pattern_demands: list[PatternDemand] = Field(default_factory=list)
    group_demands: list[GroupDemand] = Field(default_factory=list)
    carry_over: list[PeriodCarryOver] = Field(default_factory=list)
    config: SolverConfig = Field(default_factory=SolverConfig)


class Assignment(BaseModel):
    member_id: str
    date: date
    pattern_id: Optional[str] = None
    is_rest: bool = False


class Violation(BaseModel):
    priority: str
    constraint_group: str
    constraint_type: str
    target_member_id: Optional[str] = None
    target_date: Optional[date] = None
    setting_value: str = ""
    actual_value: str = ""
    contributing_factors: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class SolverWarning(BaseModel):
    warning_type: str  # "pre_solve" or "post_solve"
    severity: str  # "info", "warning", "error"
    target: str = ""
    message: str = ""


class ScoreBreakdown(BaseModel):
    personal: float = 100.0
    group: float = 100.0
    demand: float = 100.0
    balance: float = 100.0


class SolverOutput(BaseModel):
    status: str  # "optimal", "feasible", "infeasible", "timeout"
    solve_time_seconds: float = 0.0
    total_penalty: int = 0
    health_score: float = 100.0
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    assignments: list[Assignment] = Field(default_factory=list)
    violations: list[Violation] = Field(default_factory=list)
    warnings: list[SolverWarning] = Field(default_factory=list)
