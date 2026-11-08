"""Stable, typed v1 contracts for item catalog reads."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CatalogModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class CatalogSourceRead(CatalogModel):
    id: int
    name: str
    base_url: str
    terms_url: str
    attribution_text: str
    license_status: str


class GameVersionRead(CatalogModel):
    game_key: str
    build: str | None
    observed_at: datetime


class ItemStatRead(CatalogModel):
    stat_type: str
    value: float


class ItemEffectRead(CatalogModel):
    effect_type: str
    description: str | None
    spell_id: int | None


class ItemRestrictionRead(CatalogModel):
    restriction_type: str
    restriction_value: str
    verification_status: str


class DataQualityIssueRead(CatalogModel):
    field_name: str
    issue_code: str
    message: str
    observed_values: dict[str, object] | list[object] | None


class CatalogItemRead(CatalogModel):
    id: int
    source_item_id: int
    name: str
    quality: str | None
    item_level: int | None
    required_level: int | None
    inventory_type: str | None
    armor_type: str | None
    weapon_type: str | None
    icon_url: str | None
    source_item_url: str | None
    wowhead_url: str | None
    availability_status: str
    verification_status: str
    created_at: datetime
    updated_at: datetime
    source: CatalogSourceRead
    game_version: GameVersionRead
    stats: list[ItemStatRead]
    effects: list[ItemEffectRead]
    restrictions: list[ItemRestrictionRead]
    quality_issues: list[DataQualityIssueRead]


class CatalogPage[T](CatalogModel):
    items: list[T]
    page: int
    page_size: int
    total: int
    pages: int


class QualityCount(CatalogModel):
    quality: str
    count: int


class VerificationCount(CatalogModel):
    verification_status: str
    count: int


class ActiveDataSource(CatalogSourceRead):
    last_checked_at: datetime | None


class CatalogSummary(CatalogModel):
    total_items: int
    items_by_quality: list[QualityCount]
    items_by_verification_status: list[VerificationCount]
    inventory_types: list[str]
    last_import_at: datetime | None
    active_data_sources: list[ActiveDataSource]
