from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_tenant_id
from ..models.member import Member
from ..schemas.common import MemberCreate, MemberResponse

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
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    member = Member(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=body.name,
        available_pattern_ids=body.available_pattern_ids,
    )
    db.add(member)
    await db.commit()
    return MemberResponse(id=member.id, name=member.name, available_pattern_ids=member.available_pattern_ids or [])


@router.put("/{member_id}", response_model=MemberResponse)
async def update_member(
    member_id: str,
    body: MemberCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Member).where(Member.id == member_id, Member.tenant_id == tenant_id))
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    member.name = body.name
    member.available_pattern_ids = body.available_pattern_ids
    await db.commit()
    return MemberResponse(id=member.id, name=member.name, available_pattern_ids=member.available_pattern_ids or [])


@router.delete("/{member_id}", status_code=204)
async def delete_member(
    member_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Member).where(Member.id == member_id, Member.tenant_id == tenant_id))
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    await db.delete(member)
    await db.commit()


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
