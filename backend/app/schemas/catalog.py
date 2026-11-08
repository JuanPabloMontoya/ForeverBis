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


class AcquisitionSourceRead(CatalogModel):
    source_type: str
    name: str | None
    external_id: str | None
    location: str | None
    zone_name: str | None
    difficulty: str | None
    faction_requirement: str | None
    conditions: dict[str, object] | None
    source_url: str | None
    verification_status: str
    captured_at: datetime | None


class ItemAcquisitionRead(CatalogModel):
    verification_status: str
    requirements: str | None
    acquisition_source: AcquisitionSourceRead


class DataQualityIssueRead(CatalogModel):
    field_name: str
    issue_code: str
    message: str
    observed_values: dict[str, object] | list[object] | str | int | float | bool | None


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
    armor_value: float | None
    weapon_damage_min: float | None
    weapon_damage_max: float | None
    weapon_speed: float | None
    availability_status: str
    verification_status: str
    data_quality_status: str
    field_provenance: dict[str, str]
    eligibility_status: str
    statistics_status: str
    last_validated_at: datetime | None
    imported_at: datetime | None
    last_successful_refresh_at: datetime | None
    created_at: datetime
    updated_at: datetime
    source: CatalogSourceRead
    game_version: GameVersionRead
    stats: list[ItemStatRead]
    effects: list[ItemEffectRead]
    restrictions: list[ItemRestrictionRead]
    acquisitions: list[ItemAcquisitionRead]
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
