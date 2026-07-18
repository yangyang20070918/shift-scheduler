from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_tenant_id
from ..models.pattern import ForbiddenTransition, PatternChain


router = APIRouter(prefix="/api", tags=["pattern-rules"])


class ForbiddenTransitionCreate(BaseModel):
    from_pattern_id: str
    to_pattern_id: str


class ForbiddenTransitionResponse(ForbiddenTransitionCreate):
    id: str


@router.get("/forbidden-transitions", response_model=list[ForbiddenTransitionResponse])
async def list_forbidden_transitions(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ForbiddenTransition).where(ForbiddenTransition.tenant_id == tenant_id)
    )
    return [
        ForbiddenTransitionResponse(id=ft.id, from_pattern_id=ft.from_pattern_id, to_pattern_id=ft.to_pattern_id)
        for ft in result.scalars().all()
    ]


@router.post("/forbidden-transitions", response_model=ForbiddenTransitionResponse, status_code=201)
async def create_forbidden_transition(
    body: ForbiddenTransitionCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(ForbiddenTransition).where(
            ForbiddenTransition.tenant_id == tenant_id,
            ForbiddenTransition.from_pattern_id == body.from_pattern_id,
            ForbiddenTransition.to_pattern_id == body.to_pattern_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This transition is already forbidden")

    ft = ForbiddenTransition(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        from_pattern_id=body.from_pattern_id,
        to_pattern_id=body.to_pattern_id,
    )
    db.add(ft)
    await db.commit()
    return ForbiddenTransitionResponse(id=ft.id, from_pattern_id=ft.from_pattern_id, to_pattern_id=ft.to_pattern_id)


@router.delete("/forbidden-transitions/{ft_id}", status_code=204)
async def delete_forbidden_transition(
    ft_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ForbiddenTransition).where(
            ForbiddenTransition.id == ft_id,
            ForbiddenTransition.tenant_id == tenant_id,
        )
    )
    ft = result.scalar_one_or_none()
    if ft is None:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(ft)
    await db.commit()


class ChainNodeSchema(BaseModel):
    day_offset: int
    candidates: list[str] = []
    is_rest: bool = False


class PatternChainCreate(BaseModel):
    name: str = ""
    trigger_pattern_id: str
    nodes: list[ChainNodeSchema] = []


class PatternChainResponse(PatternChainCreate):
    id: str
    total_length: int


@router.get("/pattern-chains", response_model=list[PatternChainResponse])
async def list_pattern_chains(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PatternChain).where(PatternChain.tenant_id == tenant_id)
    )
    return [
        PatternChainResponse(
            id=c.id, name=c.name or "",
            trigger_pattern_id=c.trigger_pattern_id,
            nodes=[ChainNodeSchema(**n) for n in (c.nodes or [])],
            total_length=c.total_length or 0,
        )
        for c in result.scalars().all()
    ]


@router.post("/pattern-chains", response_model=PatternChainResponse, status_code=201)
async def create_pattern_chain(
    body: PatternChainCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    total_length = 1 + len(body.nodes)
    chain = PatternChain(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=body.name,
        trigger_pattern_id=body.trigger_pattern_id,
        nodes=[n.model_dump() for n in body.nodes],
        total_length=total_length,
    )
    db.add(chain)
    await db.commit()
    return PatternChainResponse(
        id=chain.id, name=chain.name or "",
        trigger_pattern_id=chain.trigger_pattern_id,
        nodes=body.nodes,
        total_length=total_length,
    )


@router.put("/pattern-chains/{chain_id}", response_model=PatternChainResponse)
async def update_pattern_chain(
    chain_id: str,
    body: PatternChainCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PatternChain).where(
            PatternChain.id == chain_id,
            PatternChain.tenant_id == tenant_id,
        )
    )
    chain = result.scalar_one_or_none()
    if chain is None:
        raise HTTPException(status_code=404, detail="Not found")
    chain.name = body.name
    chain.trigger_pattern_id = body.trigger_pattern_id
    chain.nodes = [n.model_dump() for n in body.nodes]
    chain.total_length = 1 + len(body.nodes)
    await db.commit()
    return PatternChainResponse(
        id=chain.id, name=chain.name or "",
        trigger_pattern_id=chain.trigger_pattern_id,
        nodes=body.nodes,
        total_length=chain.total_length,
    )


@router.delete("/pattern-chains/{chain_id}", status_code=204)
async def delete_pattern_chain(
    chain_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PatternChain).where(
            PatternChain.id == chain_id,
            PatternChain.tenant_id == tenant_id,
        )
    )
    chain = result.scalar_one_or_none()
    if chain is None:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(chain)
    await db.commit()
