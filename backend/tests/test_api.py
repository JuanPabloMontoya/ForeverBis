"""FastAPI startup, contracts, health, and error behavior."""

from fastapi import APIRouter
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from backend.app.core.config import Settings
from backend.app.db.session import check_database_connection
from backend.app.main import create_app


def make_settings() -> Settings:
    return Settings(
        app_name="Forever BIS Test",
        app_version="0.1.0-test",
        app_env="test",
        log_level="ERROR",
        database_url="postgresql+psycopg://test:test@localhost:5432/test",
        api_cors_origins="http://testserver",
    )


def test_application_starts_and_exposes_openapi():
    app = create_app(make_settings(), db_health_check=lambda: True)
    with TestClient(app) as client:
        assert client.get("/openapi.json").status_code == 200
        assert client.get("/api/v1/health").status_code == 200


def test_root_returns_application_metadata(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "name": "Forever BIS Test",
        "version": "0.1.0-test",
        "api_version": "v1",
        "environment": "test",
    }


def test_health_reports_database_available(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["database"] == "healthy"
    assert response.json()["checked_at"]


def test_frontend_origin_is_allowed_by_cors():
    settings = make_settings().model_copy(update={"api_cors_origins": "http://localhost:5173"})
    app = create_app(settings, db_health_check=lambda: True)
    with TestClient(app) as client:
        response = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_health_reports_database_unavailable(settings):
    app = create_app(settings, db_health_check=lambda: False)
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "unavailable"


def test_health_catches_database_connectivity_exception(settings):
    def unavailable():
        raise ConnectionError("database offline")

    app = create_app(settings, db_health_check=unavailable)
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.json()["database"] == "unavailable"


def test_database_health_query_uses_select_one():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        assert check_database_connection(engine) is True
    finally:
        engine.dispose()


def test_http_errors_use_api_error_contract(settings):
    app = create_app(settings, db_health_check=lambda: True)
    with TestClient(app) as client:
        response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"code": "http_error", "message": "Not Found"}


def test_validation_errors_use_api_error_contract(settings):
    app = create_app(settings, db_health_check=lambda: True)
    test_router = APIRouter()

    @test_router.get("/validation-probe")
    def validation_probe(required_number: int):
        return {"required_number": required_number}

    app.include_router(test_router)
    with TestClient(app) as client:
        response = client.get("/validation-probe?required_number=invalid")
    assert response.status_code == 422
    assert response.json() == {
        "code": "validation_error",
        "message": "Request validation failed.",
    }


def test_unhandled_errors_are_sanitized(settings):
    app = create_app(settings, db_health_check=lambda: True)
    test_router = APIRouter()

    @test_router.get("/error-probe")
    def error_probe():
        raise RuntimeError("sensitive internal detail")

    app.include_router(test_router)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/error-probe")
    assert response.status_code == 500
    assert response.json() == {
        "code": "internal_error",
        "message": "An unexpected server error occurred.",
    }
