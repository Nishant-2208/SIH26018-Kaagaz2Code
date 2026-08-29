"""
FastAPI dependency functions shared across routes.

  get_current_user  — decode Bearer token → User (or 401)
  require_roles     — factory that wraps get_current_user with an RBAC check
"""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.database import get_db
from app.db.models.user import User
from app.services.auth_service import get_user_by_email

# FastAPI will look for "Authorization: Bearer <token>" in request headers.
# tokenUrl is the path clients use to obtain tokens (for Swagger UI).
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(_oauth2_scheme),
    db: Session = Depends(get_db),  # noqa: B008
) -> User:
    """
    Decode the Bearer token and return the authenticated User.

    Raises HTTP 401 for:
      - missing / malformed token
      - expired token
      - token sub does not map to an active user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        email: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if email is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_roles(*roles: str) -> Callable:
    """
    RBAC dependency factory.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_roles("admin"))])

    Returns a FastAPI dependency that first validates the token (via
    get_current_user) then checks that the user's role is in `roles`.
    Raises HTTP 403 if the role is not permitted.
    """

    def _check_role(
        current_user: User = Depends(get_current_user),  # noqa: B008
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return _check_role
