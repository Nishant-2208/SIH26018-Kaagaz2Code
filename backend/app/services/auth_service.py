"""
Auth service — business logic for authentication.

Routes call this; this calls the DB and security primitives.
Never put raw SQLAlchemy queries in route handlers.
"""

from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.db.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return the User with the given email, or None if not found."""
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """
    Validate email + password.

    Returns the User on success, None on failure (wrong email or wrong
    password — deliberately indistinguishable to callers).
    """
    user = get_user_by_email(db, email)
    if user is None:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
