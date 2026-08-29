"""
Security utilities: password hashing and JWT token management.

Intentionally thin — no business logic here. Business logic (e.g.
"is this user allowed to log in?") lives in app/services/auth_service.py.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if `plain_password` matches the stored bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Return a bcrypt hash suitable for storing in the database."""
    return _pwd_context.hash(password)


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------


def create_access_token(data: dict[str, Any]) -> str:
    """
    Create a signed JWT access token.

    The payload is a copy of `data` with an `exp` claim appended.
    Expiry is set to JWT_ACCESS_TOKEN_EXPIRE_MINUTES from settings.
    """
    payload = data.copy()
    expire = datetime.now(tz=timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload.update({"exp": expire, "type": "access"})
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Create a signed JWT refresh token.

    Longer-lived than the access token (JWT_REFRESH_TOKEN_EXPIRE_DAYS).
    """
    payload = data.copy()
    expire = datetime.now(tz=timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload.update({"exp": expire, "type": "refresh"})
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT token.

    Raises `jose.JWTError` on invalid/expired tokens — callers are
    responsible for translating this into an HTTP 401.
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
