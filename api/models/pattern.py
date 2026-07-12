from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TenantMixin, TimestampMixin


class ShiftPattern(Base, TenantMixin, TimestampMixin):
    __tablename__ = "shift_patterns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="NORMAL")
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)  # "HH:MM"
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    break_hours: Mapped[float] = mapped_column(Float, default=0.0)
    work_hours: Mapped[float] = mapped_column(Float, nullable=False)
    is_companion: Mapped[bool] = mapped_column(Boolean, default=False)
    color_code: Mapped[str] = mapped_column(String(7), default="#808080")


class ForbiddenTransition(Base, TenantMixin):
    __tablename__ = "forbidden_transitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    from_pattern_id: Mapped[str] = mapped_column(String(36), nullable=False)
    to_pattern_id: Mapped[str] = mapped_column(String(36), nullable=False)


class PatternChain(Base, TenantMixin, TimestampMixin):
    __tablename__ = "pattern_chains"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    trigger_pattern_id: Mapped[str] = mapped_column(String(36), nullable=False)
    nodes: Mapped[list] = mapped_column(JSON, default=list)  # [{day_offset, candidates, is_rest}]
    total_length: Mapped[int] = mapped_column(default=0)
