"""
Auth routes: login, token refresh, current-user profile.

POST /auth/login   — email + password → access + refresh tokens
POST /auth/refresh — refresh token → new access token
GET  /auth/me      — returns authenticated user's profile
"""

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserResponse
from app.services.auth_service import authenticate_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Obtain access and refresh tokens",
)
def login(
    payload: LoginRequest, db: Session = Depends(get_db)  # noqa: B008
) -> TokenResponse:
    """
    Authenticate with email and password.

    Returns a short-lived access token and a long-lived refresh token.
    Returns HTTP 401 on invalid credentials (email not found, wrong
    password, or inactive account) — deliberately no distinction between
    "user not found" and "wrong password" to avoid user enumeration.
    """
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = {"sub": user.email, "role": user.role}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange a refresh token for a new access token",
)
def refresh(
    payload: RefreshRequest, db: Session = Depends(get_db)  # noqa: B008
) -> TokenResponse:
    """
    Issue a new access token using a valid refresh token.

    The original refresh token is returned unchanged so clients don't need
    to update their stored refresh token on every call.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        decoded = decode_token(payload.refresh_token)
        if decoded.get("type") != "refresh":
            raise credentials_exception
        email: str | None = decoded.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Verify the user still exists and is active
    from app.services.auth_service import get_user_by_email

    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        raise credentials_exception

    token_data = {"sub": user.email, "role": user.role}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=payload.refresh_token,  # return unchanged
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Return the current authenticated user's profile",
)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:  # noqa: B008
    """Requires a valid Bearer access token."""
    return UserResponse.model_validate(current_user)
