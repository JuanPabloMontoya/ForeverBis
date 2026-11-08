"""Version 1 API contracts, independent from persistence."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["healthy", "degraded"]
    database: Literal["healthy", "unavailable"]
    checked_at: datetime


class ApplicationInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    api_version: str
    environment: str


class APIError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
