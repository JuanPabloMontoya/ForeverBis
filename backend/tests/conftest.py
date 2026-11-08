"""Shared fixtures for API and infrastructure tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from backend.app.core.config import Settings
from backend.app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_name="Forever BIS Test",
        app_version="0.1.0-test",
        app_env="test",
        log_level="ERROR",
        database_url="postgresql+psycopg://test:test@localhost:5432/test",
        api_cors_origins="http://testserver",
    )


@pytest.fixture
def app(settings):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    return create_app(settings, engine=engine, db_health_check=lambda: True)


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client
