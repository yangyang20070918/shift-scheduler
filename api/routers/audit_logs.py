from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_tenant_id
from ..models.audit_log import AuditLog

router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])


class AuditLogResponse(BaseModel):
    id: str
    timestamp: str
    user_id: str | None = None
    user_email: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    detail: dict | None = None
    ip_address: str | None = None


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int


class AuditStatItem(BaseModel):
    key: str
    count: int


class AuditStatsResponse(BaseModel):
    by_action: list[AuditStatItem]
    by_resource: list[AuditStatItem]
    by_user: list[AuditStatItem]
    total: int


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    user_id: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    q = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    count_q = select(func.count(AuditLog.id)).where(AuditLog.tenant_id == tenant_id)

    if action:
        q = q.where(AuditLog.action == action)
        count_q = count_q.where(AuditLog.action == action)
    if resource_type:
        q = q.where(AuditLog.resource_type == resource_type)
        count_q = count_q.where(AuditLog.resource_type == resource_type)
    if user_id:
        q = q.where(AuditLog.user_id == user_id)
        count_q = count_q.where(AuditLog.user_id == user_id)
    if date_from:
        dt_from = datetime.combine(date_from, time.min)
        q = q.where(AuditLog.timestamp >= dt_from)
        count_q = count_q.where(AuditLog.timestamp >= dt_from)
    if date_to:
        dt_to = datetime.combine(date_to, time.max)
        q = q.where(AuditLog.timestamp <= dt_to)
        count_q = count_q.where(AuditLog.timestamp <= dt_to)

    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    q = q.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
    result = await db.execute(q)
    logs = result.scalars().all()

    items = [
        AuditLogResponse(
            id=log.id,
            timestamp=log.timestamp.isoformat() if log.timestamp else "",
            user_id=log.user_id,
            user_email=log.user_email,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            detail=log.detail,
            ip_address=log.ip_address,
        )
        for log in logs
    ]
    return AuditLogListResponse(items=items, total=total)


@router.get("/stats", response_model=AuditStatsResponse)
async def audit_stats(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
):
    base = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    if date_from:
        base = base.where(AuditLog.timestamp >= datetime.combine(date_from, time.min))
    if date_to:
        base = base.where(AuditLog.timestamp <= datetime.combine(date_to, time.max))

    base_where = base.whereclause

    action_q = select(AuditLog.action, func.count(AuditLog.id)).where(base_where).group_by(AuditLog.action)
    resource_q = select(AuditLog.resource_type, func.count(AuditLog.id)).where(base_where).group_by(AuditLog.resource_type)
    user_q = select(AuditLog.user_email, func.count(AuditLog.id)).where(base_where).group_by(AuditLog.user_email)
    total_q = select(func.count(AuditLog.id)).where(base_where)

    action_r, resource_r, user_r, total_r = await db.execute(action_q), await db.execute(resource_q), await db.execute(user_q), await db.execute(total_q)

    return AuditStatsResponse(
        by_action=[AuditStatItem(key=r[0], count=r[1]) for r in action_r.all()],
        by_resource=[AuditStatItem(key=r[0], count=r[1]) for r in resource_r.all()],
        by_user=[AuditStatItem(key=r[0] or "system", count=r[1]) for r in user_r.all()],
        total=total_r.scalar() or 0,
    )
