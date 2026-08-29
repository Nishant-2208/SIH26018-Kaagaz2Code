"""
Import every ORM model module here so that Base.metadata is fully populated
before Alembic autogenerate runs, and so `from app.db.models import User`
style imports work.
"""

from app.db.models.user import User

__all__ = ["User"]
