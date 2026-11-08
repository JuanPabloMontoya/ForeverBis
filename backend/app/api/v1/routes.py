"""Version 1 HTTP routes."""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Request

from backend.app.schemas.v1 import ApplicationInfo, HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(request: Request) -> HealthResponse:
    checker = request.app.state.db_health_check
    try:
        is_available = bool(checker())
    except Exception:
        logger.warning("Database health check failed", exc_info=True)
        is_available = False
    database = "healthy" if is_available else "unavailable"
    return HealthResponse(
        status="healthy" if is_available else "degraded",
        database=database,
        checked_at=datetime.now(UTC),
    )


def application_info(request: Request) -> ApplicationInfo:
    settings = request.app.state.settings
    return ApplicationInfo(
        name=settings.app_name,
        version=settings.app_version,
        api_version="v1",
        environment=settings.app_env,
    )
