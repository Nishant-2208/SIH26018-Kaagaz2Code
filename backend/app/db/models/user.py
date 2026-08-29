"""
User ORM model.

All schema changes must go through Alembic migrations — never use
Base.metadata.create_all() or table auto-creation in application code.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class UserRole(str):
    """Role constants — kept as plain strings so they serialize cleanly to JSON."""

    CITIZEN = "citizen"
    OFFICER = "officer"
    REVIEWER = "reviewer"
    ADMIN = "admin"


_ROLE_ENUM = Enum(
    "citizen",
    "officer",
    "reviewer",
    "admin",
    name="userrole",  # PostgreSQL enum type name
)


class User(Base):
    """
    Application user.

    Roles:
      citizen  — submits land record requests
      officer  — processes / enters data
      reviewer — reviews flagged records
      admin    — full platform access
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(320),  # RFC 5321 max
        unique=True,
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        _ROLE_ENUM,
        nullable=False,
        default="citizen",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role!r}>"
