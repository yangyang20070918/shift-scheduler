from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user, get_tenant_id
from ..models.member import Member
from ..models.user import User
from ..schemas.common import MemberCreate, MemberResponse
from ..services.audit import record_audit

router = APIRouter(prefix="/api/members", tags=["members"])


@router.get("", response_model=list[MemberResponse])
async def list_members(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Member).where(Member.tenant_id == tenant_id))
    members = result.scalars().all()
    return [MemberResponse(id=m.id, name=m.name, available_pattern_ids=m.available_pattern_ids or []) for m in members]


@router.post("", response_model=MemberResponse, status_code=201)
async def create_member(
    body: MemberCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = Member(
        id=str(uuid.uuid4()),
        tenant_id=user.tenant_id,
        name=body.name,
        available_pattern_ids=body.available_pattern_ids,
    )
    db.add(member)
    await db.commit()
    await record_audit(db, tenant_id=user.tenant_id, action="CREATE", resource_type="member",
                       user_id=user.id, user_email=user.email, resource_id=member.id,
                       detail={"name": body.name}, request=request)
    return MemberResponse(id=member.id, name=member.name, available_pattern_ids=member.available_pattern_ids or [])


@router.put("/{member_id}", response_model=MemberResponse)
async def update_member(
    member_id: str,
    body: MemberCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Member).where(Member.id == member_id, Member.tenant_id == user.tenant_id))
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    old_name = member.name
    member.name = body.name
    member.available_pattern_ids = body.available_pattern_ids
    await db.commit()
    await record_audit(db, tenant_id=user.tenant_id, action="UPDATE", resource_type="member",
                       user_id=user.id, user_email=user.email, resource_id=member_id,
                       detail={"old_name": old_name, "new_name": body.name}, request=request)
    return MemberResponse(id=member.id, name=member.name, available_pattern_ids=member.available_pattern_ids or [])


@router.delete("/{member_id}", status_code=204)
async def delete_member(
    member_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Member).where(Member.id == member_id, Member.tenant_id == user.tenant_id))
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    name = member.name
    await db.delete(member)
    await db.commit()
    await record_audit(db, tenant_id=user.tenant_id, action="DELETE", resource_type="member",
                       user_id=user.id, user_email=user.email, resource_id=member_id,
                       detail={"name": name}, request=request)


@router.post("/{member_id}/token")
async def generate_personal_token(
    member_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Member).where(Member.id == member_id, Member.tenant_id == tenant_id))
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    member.personal_token = str(uuid.uuid4())
    await db.commit()
    return {"member_id": member.id, "personal_token": member.personal_token}


@router.get("/{member_id}/token")
async def get_personal_token(
    member_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Member).where(Member.id == member_id, Member.tenant_id == tenant_id))
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"member_id": member.id, "personal_token": member.personal_token}
