from uuid import UUID

from pydantic import EmailStr, Field
from sentinelai_contracts import Role

from app.schemas.common import APIModel


class LoginRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=8)


class RegisterRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    role: Role = Role.VIEWER


class TokenPair(APIModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(APIModel):
    refresh_token: str


class UserOut(APIModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
