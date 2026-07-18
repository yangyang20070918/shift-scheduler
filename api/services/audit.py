from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.audit_log import AuditLog

logger = logging.getLogger(__name__)

DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE")


def _get_dynamodb_table():
    import boto3
    dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "ap-northeast-1"))
    return dynamodb.Table(DYNAMODB_TABLE)


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

    now = datetime.now(timezone.utc)
    log_id = str(uuid.uuid4())

    # Always write to RDS (SQLAlchemy)
    log = AuditLog(
        id=log_id,
        tenant_id=tenant_id,
        timestamp=now,
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

    # Also write to DynamoDB if configured
    if DYNAMODB_TABLE:
        try:
            table = _get_dynamodb_table()
            item = {
                "tenant_id": tenant_id,
                "timestamp_id": f"{now.isoformat()}#{log_id}",
                "user_id": user_id or "",
                "user_email": user_email or "",
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id or "",
                "detail": json.dumps(detail) if detail else "",
                "ip_address": ip or "",
                "user_agent": ua or "",
            }
            table.put_item(Item=item)
        except Exception:
            logger.exception("Failed to write audit log to DynamoDB")
