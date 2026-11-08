"""Public and local-operator contracts for imports and contributions."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SLOTS = {
    "head",
    "neck",
    "shoulders",
    "back",
    "chest",
    "wrist",
    "hands",
    "waist",
    "legs",
    "feet",
    "ring_1",
    "ring_2",
    "trinket_1",
    "trinket_2",
    "main_hand",
    "off_hand",
    "ranged",
}


class OperationsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SuggestionCreate(OperationsModel):
    class_name: str = Field(min_length=1, max_length=30)
    specialization: str = Field(min_length=1, max_length=50)
    faction: Literal["Alliance", "Horde"]
    character_level: int = Field(ge=1, le=60)
    equipment_slot: str
    suggested_item_name: str = Field(min_length=1, max_length=250)
    wowhead_url: str = Field(min_length=1, max_length=500)
    explanation: str | None = Field(default=None, max_length=4000)
    supporting_evidence: str | None = Field(default=None, max_length=4000)

    @field_validator("equipment_slot")
    @classmethod
    def validate_slot(cls, value: str) -> str:
        normalized = value.strip().casefold().replace(" ", "_")
        if normalized not in SLOTS:
            raise ValueError("Unsupported equipment slot")
        return normalized

    @field_validator("wowhead_url")
    @classmethod
    def validate_wowhead_url(cls, value: str) -> str:
        import re
        from urllib.parse import urlsplit

        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "www.wowhead.com"
            or parsed.port is not None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Use an HTTPS Wowhead Forever item URL")
        match = re.fullmatch(r"/forever/item=(\d+)(?:/[A-Za-z0-9%._-]+)?/?", parsed.path)
        if match is None or int(match.group(1)) <= 0:
            raise ValueError("URL must match /forever/item=<id>[/slug]")
        return value


class SuggestionRead(OperationsModel):
    id: UUID
    class_name: str
    specialization: str
    faction: str
    character_level: int
    equipment_slot: str
    suggested_item_name: str
    wowhead_item_id: int
    submitted_url: str
    explanation: str | None
    supporting_evidence: str | None
    status: str
    submitted_at: datetime
    duplicate_flagged: bool


class ImportSnapshotRead(OperationsModel):
    id: int
    provider_build: str | None
    search_query: str | None
    requested_limit: int
    status: str
    started_at: datetime
    finished_at: datetime | None
    fetched_count: int
    imported_count: int
    updated_count: int
    skipped_count: int
    failed_count: int
    needs_review_count: int
    quality_counts: dict[str, int]
    error_summary: str | None


class SnapshotItemRead(OperationsModel):
    id: int
    item_id: int | None
    source_item_id: int
    outcome: str
    changed_fields: list[str]
    provider_etag: str | None
    captured_at: datetime
    failure_reason: str | None


class PatchRead(OperationsModel):
    id: int
    patch_key: str
    label: str
    status: str
    created_at: datetime
