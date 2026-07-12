from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_tenant_id
from ..models.member import Member
from ..models.pattern import ShiftPattern

router = APIRouter(prefix="/api/import", tags=["import"])


@router.get("/template")
async def download_template():
    from ..services.import_excel import generate_import_template
    buf = generate_import_template()
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="import_template.xlsx"'},
    )


@router.post("/preview")
async def preview_import(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    from ..services.import_excel import parse_import_excel
    parsed = parse_import_excel(content)

    patterns_q = await db.execute(select(ShiftPattern).where(ShiftPattern.tenant_id == tenant_id))
    patterns = {p.name: p.id for p in patterns_q.scalars().all()}

    members_q = await db.execute(select(Member).where(Member.tenant_id == tenant_id))
    existing_members = {m.name: m.id for m in members_q.scalars().all()}

    preview = {
        "members": [],
        "constraints": [],
        "demands": parsed.get("demands", []),
        "warnings": [],
    }

    for m in parsed.get("members", []):
        status = "update" if m["name"] in existing_members else "new"
        pattern_ids = []
        for pn in m.get("pattern_names", []):
            if pn in patterns:
                pattern_ids.append(patterns[pn])
            else:
                preview["warnings"].append(f"パターン「{pn}」が見つかりません（メンバー: {m['name']}）")
        preview["members"].append({
            "name": m["name"],
            "status": status,
            "pattern_ids": pattern_ids,
            "pattern_names": m.get("pattern_names", []),
        })

    for c in parsed.get("constraints", []):
        member_name = c.get("member_name", "")
        if member_name not in existing_members and not any(m["name"] == member_name for m in parsed.get("members", [])):
            preview["warnings"].append(f"メンバー「{member_name}」が見つかりません（個人制約）")
        preview["constraints"].append(c)

    return preview


@router.post("/execute")
async def execute_import(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    from ..services.import_excel import parse_import_excel
    parsed = parse_import_excel(content)

    patterns_q = await db.execute(select(ShiftPattern).where(ShiftPattern.tenant_id == tenant_id))
    patterns = {p.name: p.id for p in patterns_q.scalars().all()}

    members_q = await db.execute(select(Member).where(Member.tenant_id == tenant_id))
    existing_members = {m.name: m for m in members_q.scalars().all()}

    created = 0
    updated = 0

    for m_data in parsed.get("members", []):
        pattern_ids = [patterns[pn] for pn in m_data.get("pattern_names", []) if pn in patterns]
        if m_data["name"] in existing_members:
            member = existing_members[m_data["name"]]
            member.available_pattern_ids = pattern_ids
            updated += 1
        else:
            member = Member(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name=m_data["name"],
                available_pattern_ids=pattern_ids,
            )
            db.add(member)
            existing_members[m_data["name"]] = member
            created += 1

    from ..models.constraint import PersonConstraint
    for c_data in parsed.get("constraints", []):
        member_name = c_data.get("member_name", "")
        member = existing_members.get(member_name)
        if not member:
            continue
        pc_q = await db.execute(
            select(PersonConstraint).where(
                PersonConstraint.tenant_id == tenant_id,
                PersonConstraint.member_id == member.id,
            )
        )
        pc = pc_q.scalar_one_or_none()
        if pc is None:
            pc = PersonConstraint(id=str(uuid.uuid4()), tenant_id=tenant_id, member_id=member.id)
            db.add(pc)
        for field in ["weekly_work_days_min", "weekly_work_days_max", "period_work_days_min",
                       "period_work_days_max", "max_consecutive_work_days", "max_consecutive_rest_days"]:
            if field in c_data:
                setattr(pc, field, c_data[field])

    await db.commit()

    return {
        "members_created": created,
        "members_updated": updated,
        "constraints_processed": len(parsed.get("constraints", [])),
        "demands_count": len(parsed.get("demands", [])),
    }
