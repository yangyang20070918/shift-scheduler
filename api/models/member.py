from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TenantMixin, TimestampMixin


class Member(Base, TenantMixin, TimestampMixin):
    __tablename__ = "members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    available_pattern_ids: Mapped[list] = mapped_column(JSON, default=list)
    personal_token: Mapped[str | None] = mapped_column(String(36), nullable=True, unique=True)
