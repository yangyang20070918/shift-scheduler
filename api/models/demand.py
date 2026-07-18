from __future__ import annotations

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TenantMixin


class DailyDemand(Base, TenantMixin):
    __tablename__ = "daily_demands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    schedule_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    date: Mapped[str] = mapped_column(Date, nullable=False)
    min_total: Mapped[int] = mapped_column(Integer, default=0)
    max_total: Mapped[int] = mapped_column(Integer, default=999)


class PatternDemand(Base, TenantMixin):
    __tablename__ = "pattern_demands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    schedule_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    date: Mapped[str] = mapped_column(Date, nullable=False)
    pattern_id: Mapped[str] = mapped_column(String(36), nullable=False)
    min_count: Mapped[int] = mapped_column(Integer, default=0)


class GroupDemand(Base, TenantMixin):
    __tablename__ = "group_demands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    schedule_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    date: Mapped[str] = mapped_column(Date, nullable=False)
    group_id: Mapped[str] = mapped_column(String(36), nullable=False)
    pattern_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    min_count: Mapped[int] = mapped_column(Integer, default=0)
