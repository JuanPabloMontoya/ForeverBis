"""Versioned API contracts for eligibility checks and transparent item scoring."""

from pydantic import BaseModel, ConfigDict, Field


class ScoringProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_name: str
    specialization: str
    role: str | None
    version: str
    active: bool
    provisional: bool
    assumptions: str
    stat_weights: dict[str, float]
    adjustments: dict[str, float]


class CharacterRequest(BaseModel):
    class_name: str = Field(min_length=1, max_length=30)
    specialization: str = Field(min_length=1, max_length=50)
    faction: str = Field(min_length=1, max_length=20)
    level: int = Field(ge=1, le=60)
    race: str | None = Field(default=None, max_length=30)


class EligibilityRead(BaseModel):
    status: str
    reasons: list[str]


class ContributionRead(BaseModel):
    stat_type: str
    value: float
    weight: float
    contribution: float


class ScoreRead(BaseModel):
    item_id: int
    item_name: str
    status: str
    score: float | None
    eligibility: EligibilityRead
    contributions: list[ContributionRead]
    missing_information: list[str]
    unsupported_statistics: list[str]
    unweighted_statistics: list[str]
    provisional: bool
    profile_version: str
    calculation_version: str


class ItemCheckRequest(CharacterRequest):
    slot: str | None = None


class ItemCompareRequest(CharacterRequest):
    slot: str
    item_ids: list[int] = Field(min_length=1, max_length=100)


class ItemComparisonRead(BaseModel):
    slot: str
    items: list[ScoreRead]
    ranked: bool
    explanation: str
