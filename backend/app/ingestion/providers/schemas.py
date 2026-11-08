"""Validated external TheWoWDB response contracts (not domain models)."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class ProviderModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ProviderLinks(ProviderModel):
    html: str | None = None
    api: str | None = None
    tooltip: str | None = None
    next: str | None = None


class ProviderAttribution(ProviderModel):
    required: bool = True
    terms: str | None = None
    text: str | None = None
    url: str | None = None


class ItemListRecord(ProviderModel):
    id: StrictInt = Field(gt=0)
    kind: Literal["item"]
    version: Literal["forever"]
    name: str = Field(min_length=1, max_length=250)
    quality: str | None = None
    item_level: StrictInt | None = Field(default=None, ge=0)
    required_level: StrictInt | None = Field(default=None, ge=0)
    links: ProviderLinks | None = None


class ItemListResponse(ProviderModel):
    version: Literal["forever"]
    kind: Literal["item"]
    build: str | None = None
    page: StrictInt = Field(ge=1)
    per_page: StrictInt = Field(ge=1, le=100)
    q: str | None = Field(default=None, max_length=64)
    count: StrictInt = Field(ge=0)
    total: StrictInt | None = Field(default=None, ge=0)
    has_more: bool
    links: ProviderLinks | None = None
    results: list[ItemListRecord]


class ItemResponse(ProviderModel):
    id: StrictInt = Field(gt=0)
    kind: Literal["item"]
    version: Literal["forever"]
    version_label: str | None = None
    build: str | None = None
    name: str = Field(min_length=1, max_length=250)
    quality: str | None = None
    item_level: StrictInt | None = Field(default=None, ge=0)
    required_level: StrictInt | None = Field(default=None, ge=0)
    item_type: str | None = None
    item_subtype: str | None = None
    slot: str | None = None
    armor: dict[str, Any] | None = None
    weapon: dict[str, Any] | None = None
    stats: list[Any] | None = None
    effects: list[Any] | None = None
    classes: list[Any] | None = None
    races: list[Any] | None = None
    factions: list[Any] | None = None
    unique: Any = None
    icon_url: str | None = None
    links: ProviderLinks | None = None
    attribution: ProviderAttribution | None = None


class ItemTooltipResponse(ProviderModel):
    """Documented tooltip envelope; HTML is intentionally not normalized or displayed."""

    id: StrictInt | None = None
    kind: str | None = None
    version: str | None = None
    fields: dict[str, Any] = Field(default_factory=dict)
    html: str | None = None
    attribution: ProviderAttribution | None = None
