from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class MemberCreate(BaseModel):
    name: str
    available_pattern_ids: list[str] = []


class MemberResponse(BaseModel):
    id: str
    name: str
    available_pattern_ids: list[str]


class PatternCreate(BaseModel):
    name: str
    type: str = "NORMAL"
    start_time: str
    end_time: str
    break_hours: float = 0.0
    work_hours: float
    is_companion: bool = False
    color_code: str = "#808080"


class PatternResponse(BaseModel):
    id: str
    name: str
    type: str
    start_time: str
    end_time: str
    break_hours: float
    work_hours: float
    is_companion: bool
    color_code: str


class GroupCreate(BaseModel):
    name: str
    member_ids: list[str] = []


class GroupResponse(BaseModel):
    id: str
    name: str
    member_ids: list[str]


class PersonConstraintCreate(BaseModel):
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


class PersonConstraintResponse(PersonConstraintCreate):
    id: str


class DailyDemandCreate(BaseModel):
    date: date
    min_total: int = 0
    max_total: int = 999


class DailyDemandResponse(DailyDemandCreate):
    id: str
    schedule_id: str


class DailyDemandBatch(BaseModel):
    min_total: int = 1
    max_total: int = 999


class FixedAssignmentCreate(BaseModel):
    member_id: str
    date: date
    type: str  # "work" or "rest"
    pattern_id: Optional[str] = None


class FixedAssignmentResponse(FixedAssignmentCreate):
    id: str
    schedule_id: str


class GroupDemandCreate(BaseModel):
    date: date
    group_id: str
    pattern_id: str
    min_count: int = 0


class GroupDemandResponse(GroupDemandCreate):
    id: str
    schedule_id: str


class RestDayRequestUpdate(BaseModel):
    requested_dates: list[date] = []


class RestDayRequestResponse(BaseModel):
    id: str
    schedule_id: str
    member_id: str
    member_name: str = ""
    requested_dates: list[str]
    status: str
    submitted_at: Optional[str] = None
    is_auto_submitted: bool = False


class ScheduleCreate(BaseModel):
    name: str = ""
    start_date: date
    num_days: int
    config: dict = {}
    rest_request_deadline: Optional[date] = None
    rest_request_max_days: int = 3


class ScheduleResponse(BaseModel):
    id: str
    name: str
    start_date: str
    num_days: int
    status: str
    rest_request_deadline: Optional[str] = None
    rest_request_max_days: int = 3
    result_status: Optional[str] = None
    solve_time_seconds: Optional[float] = None
    total_penalty: Optional[int] = None
    health_score: Optional[float] = None
    score_breakdown: Optional[dict] = None


class ScheduleResultResponse(BaseModel):
    id: str
    status: str
    result_status: Optional[str] = None
    solve_time_seconds: Optional[float] = None
    health_score: Optional[float] = None
    score_breakdown: Optional[dict] = None
    assignments: Optional[list] = None
    violations: Optional[list] = None
    warnings: Optional[list] = None
