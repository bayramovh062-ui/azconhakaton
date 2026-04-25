"""Auth router: /auth/login, /auth/me."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.database import get_session
from backend.models import User, Vessel

from .schemas import LoginRequest, TokenResponse, UserOut
from .utils import create_access_token, get_current_user, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    user = (
        await session.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive"
        )

    token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    vessel_name = None
    if current.vessel_id:
        vessel = await session.get(Vessel, current.vessel_id)
        vessel_name = vessel.name if vessel else None
    return UserOut(
        id=current.id,
        email=current.email,
        role=current.role,
        full_name=current.full_name,
        operator_company=current.operator_company,
        vessel_id=current.vessel_id,
        vessel_name=vessel_name,
    )
