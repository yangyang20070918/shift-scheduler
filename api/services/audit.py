from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.audit_log import AuditLog


async def record_audit(
    db: AsyncSession,
    *,
    tenant_id: str,
    action: str,
    resource_type: str,
    user_id: str | None = None,
    user_email: str | None = None,
    resource_id: str | None = None,
    detail: dict | None = None,
    request: Request | None = None,
) -> None:
    ip = None
    ua = None
    if request:
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent", "")[:300]

    log = AuditLog(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        timestamp=datetime.now(timezone.utc),
        user_id=user_id,
        user_email=user_email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(log)
    await db.commit()
