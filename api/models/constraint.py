from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TenantMixin, TimestampMixin


class PersonConstraint(Base, TenantMixin, TimestampMixin):
    __tablename__ = "person_constraints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    member_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    weekly_work_days_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weekly_work_days_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    period_work_days_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    period_work_days_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weekly_work_hours_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    weekly_work_hours_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    period_work_hours_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    period_work_hours_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_consecutive_work_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_consecutive_rest_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
