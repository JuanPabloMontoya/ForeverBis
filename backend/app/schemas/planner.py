"""Aggregated per-slot planner response contracts."""

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.catalog import CatalogItemRead
from backend.app.schemas.scoring import ScoreRead


class PlannerModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlannerCharacter(PlannerModel):
    class_name: str
    specialization: str
    faction: str
    level: int = Field(ge=1, le=60)


class PlannerCandidate(PlannerModel):
    item: CatalogItemRead
    result: ScoreRead
    score_difference: float | None = None


class PlannerSlot(PlannerModel):
    slot: str
    slot_family: str
    status: str
    recommendation: PlannerCandidate | None
    alternatives: list[PlannerCandidate]
    eligible_count: int
    incomplete_count: int
    explanation: list[str]


class GearPlanResponse(PlannerModel):
    character: PlannerCharacter
    profile_version: str
    profile_provisional: bool
    profile_configured: bool
    profile_assumptions: str
    slots: list[PlannerSlot]
