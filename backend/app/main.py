"""FastAPI application factory and executable application."""

import logging
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import Engine
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api.v1.routes import application_info
from backend.app.api.v1.routes import router as v1_router
from backend.app.core.config import Settings, get_settings
from backend.app.core.logging import configure_logging
from backend.app.db.session import (
    check_database_connection,
    create_database_engine,
    create_session_factory,
)
from backend.app.schemas.v1 import APIError, ApplicationInfo

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    engine: Engine | None = None,
    db_health_check: Callable[[], bool] | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)
    database_engine = engine or create_database_engine(active_settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        database_engine.dispose()

    app = FastAPI(
        title=active_settings.app_name,
        version=active_settings.app_version,
        description="Technical foundation for the Forever BIS planner.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.engine = database_engine
    app.state.session_factory = create_session_factory(database_engine)
    app.state.db_health_check = db_health_check or (
        lambda: check_database_connection(database_engine)
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.get("/", response_model=ApplicationInfo, tags=["system"])
    def root(request: Request) -> ApplicationInfo:
        return application_info(request)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = (
            exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
        )
        payload = APIError(code="http_error", message=detail)
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        payload = APIError(code="validation_error", message="Request validation failed.")
        return JSONResponse(status_code=422, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled request error", extra={"path": request.url.path})
        payload = APIError(code="internal_error", message="An unexpected server error occurred.")
        return JSONResponse(status_code=500, content=payload.model_dump())

    app.include_router(v1_router, prefix="/api/v1")
    return app


app = create_app()
