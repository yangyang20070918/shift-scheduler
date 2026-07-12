from __future__ import annotations

import datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TenantMixin, TimestampMixin


class RestDayRequest(Base, TenantMixin, TimestampMixin):
    __tablename__ = "rest_day_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    schedule_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    member_id: Mapped[str] = mapped_column(String(36), nullable=False)
    requested_dates: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft / submitted
    submitted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    is_auto_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
