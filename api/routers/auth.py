from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models.user import User
from ..schemas.auth import LoginResponse, RegisterRequest, UserResponse
from ..services.audit import record_audit
from ..services.auth import authenticate_user, create_access_token, register_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(req: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = await register_user(db, req.email, req.password, req.name, req.tenant_name)
    await record_audit(db, tenant_id=user.tenant_id, action="REGISTER", resource_type="user",
                       user_id=user.id, user_email=user.email, resource_id=user.id,
                       detail={"tenant_name": req.tenant_name}, request=request)
    return UserResponse(
        id=user.id, email=user.email, name=user.name,
        role=user.role, tenant_id=user.tenant_id,
    )


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form.username, form.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user.id, user.tenant_id)
    await record_audit(db, tenant_id=user.tenant_id, action="LOGIN", resource_type="session",
                       user_id=user.id, user_email=user.email, request=request)
    return LoginResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id, email=user.email, name=user.name,
        role=user.role, tenant_id=user.tenant_id,
    )
