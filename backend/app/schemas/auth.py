"""
Pydantic schemas for the auth domain.

These are the request/response shapes for /auth/* endpoints.
ORM models (SQLAlchemy) live in app/db/models — keep them separate.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public-safe view of a User — never includes hashed_password."""

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
