"""Settings validation tests."""

import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings


def test_settings_defaults_are_valid():
    settings = Settings(_env_file=None)
    assert settings.app_name == "Forever BIS"
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_database_driver_is_validated():
    with pytest.raises(ValidationError, match="postgresql\\+psycopg"):
        Settings(database_url="sqlite:///local.db", _env_file=None)


def test_invalid_log_level_is_rejected():
    with pytest.raises(ValidationError, match="LOG_LEVEL"):
        Settings(log_level="verbose", _env_file=None)
