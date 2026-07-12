from __future__ import annotations

import datetime

from sqlalchemy import JSON, Date, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TenantMixin, TimestampMixin


class Schedule(Base, TenantMixin, TimestampMixin):
    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    num_days: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft/requesting/running/completed/failed
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    # Rest request settings
    rest_request_deadline: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    rest_request_max_days: Mapped[int] = mapped_column(Integer, default=3)

    # Results (filled after solve)
    result_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    solve_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_penalty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    assignments: Mapped[list | None] = mapped_column(JSON, nullable=True)
    violations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)


class FixedAssignment(Base, TenantMixin):
    __tablename__ = "fixed_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    schedule_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    member_id: Mapped[str] = mapped_column(String(36), nullable=False)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)  # "work" or "rest"
    pattern_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
