"""
FastAPI application entrypoint.

This file only wires things together (middleware, routers, startup logging).
Business logic lives in app/services, not here.
"""

import time
import traceback
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import auth, system
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.database import SessionLocal

configure_logging()
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Step 2.2 — Request-ID context variable
# Middleware sets this per request so log calls can include the request ID.
# ---------------------------------------------------------------------------
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Generate a UUID per request, expose it as X-Request-ID response header,
    and store it in `request_id_ctx` so logger calls can include it.
    """

    async def dispatch(self, request: Request, call_next):
        req_id = str(uuid.uuid4())
        request_id_ctx.set(req_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response


# ---------------------------------------------------------------------------
# Lifespan: startup + shutdown logic (replaces deprecated @app.on_event).
# DB retry only matters when the API starts before PostgreSQL is ready
# (common in docker-compose). When running locally with DB already up,
# the first attempt succeeds immediately.
# ---------------------------------------------------------------------------
_DB_RETRY_ATTEMPTS = 5
_DB_RETRY_DELAY_S = 2


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Run startup checks, then yield (server is live), then shutdown."""
    logger.info("Starting %s in %s mode", settings.APP_NAME, settings.ENVIRONMENT)

    # --- DB connectivity check with retry ---
    for attempt in range(1, _DB_RETRY_ATTEMPTS + 1):
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            logger.info("DB connection OK (attempt %d/%d)", attempt, _DB_RETRY_ATTEMPTS)
            break
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "DB not ready (attempt %d/%d): %s",
                attempt,
                _DB_RETRY_ATTEMPTS,
                exc,
            )
            if attempt == _DB_RETRY_ATTEMPTS:
                logger.error("DB unreachable after %d attempts — continuing anyway", _DB_RETRY_ATTEMPTS)
            else:
                time.sleep(_DB_RETRY_DELAY_S)

    yield  # server is live here

    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description="Smart Land Record Digitization backend (Kaagaz2Code / SIH26018)",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# Middleware registration order: outermost first.
# RequestID must come before CORS so the header is set on every response.
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
# Phase 1: system/health checks.
# Phase 2: authentication (login, refresh, me).
app.include_router(system.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)


# ---------------------------------------------------------------------------
# Step 2.1 — Global unhandled exception handler
# Catches anything that isn't already an HTTPException (those are handled by
# FastAPI's built-in handler and continue to return their own status codes).
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = request_id_ctx.get()
    logger.error(
        "Unhandled exception [request_id=%s] %s %s\n%s",
        req_id,
        request.method,
        request.url,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Startup logic moved to the lifespan context manager above.


@app.get("/")
def root() -> dict:
    return {
        "service": settings.APP_NAME,
        "status": "running",
        "docs": f"{settings.API_V1_PREFIX}/docs",
    }
