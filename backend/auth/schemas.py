"""Auth pydantic schemas."""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    role: str
    full_name: Optional[str] = None
    operator_company: Optional[str] = None
    vessel_id: Optional[uuid.UUID] = None
    vessel_name: Optional[str] = None
