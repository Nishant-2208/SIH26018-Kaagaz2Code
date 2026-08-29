"""
System-level endpoints: liveness/readiness checks.

Used by Docker/orchestrators and by the frontend dev to confirm the API and
database are reachable before wiring up real screens.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.config import settings
from app.db.database import get_db

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    """Basic liveness probe — does not touch the database."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict:  # noqa: B008
    """Readiness probe — confirms the API can actually reach PostgreSQL."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}


@router.get(
    "/health/admin",
    summary="Admin-only liveness probe (verifies RBAC)",
    dependencies=[Depends(require_roles("admin"))],
)
def health_admin() -> dict:
    """Requires admin role — used by tests to verify require_roles returns 403 for non-admins."""
    return {"status": "ok", "role": "admin"}
