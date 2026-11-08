"""Catalog operation history and public contribution endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.community.service import submit_suggestion
from backend.app.db.session import get_session
from backend.app.models.catalog import ForeverPatch, Item, ItemStat, ScoringProfile
from backend.app.models.operations import CatalogImportSnapshot, ItemDataSnapshot, ItemSuggestion
from backend.app.schemas.operations import (
    ImportSnapshotRead,
    PatchRead,
    SnapshotItemRead,
    SuggestionCreate,
    SuggestionRead,
)

router = APIRouter(tags=["catalog operations"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/catalog/imports", response_model=list[ImportSnapshotRead])
def list_imports(
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> list[CatalogImportSnapshot]:
    return list(
        session.scalars(
            select(CatalogImportSnapshot)
            .order_by(CatalogImportSnapshot.started_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )


@router.get("/catalog/imports/{snapshot_id}", response_model=ImportSnapshotRead)
def get_import(snapshot_id: int, session: SessionDep) -> CatalogImportSnapshot:
    row = session.get(CatalogImportSnapshot, snapshot_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Import snapshot not found")
    return row


@router.get("/catalog/imports/{snapshot_id}/records", response_model=list[SnapshotItemRead])
def list_import_records(
    snapshot_id: int,
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> list[ItemDataSnapshot]:
    if session.get(CatalogImportSnapshot, snapshot_id) is None:
        raise HTTPException(status_code=404, detail="Import snapshot not found")
    return list(
        session.scalars(
            select(ItemDataSnapshot)
            .where(ItemDataSnapshot.import_snapshot_id == snapshot_id)
            .order_by(ItemDataSnapshot.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )


@router.get("/catalog/coverage")
def catalog_coverage(session: SessionDep) -> dict:
    rows = list(
        session.execute(
            select(
                Item.inventory_type,
                Item.required_level,
                Item.verification_status,
                func.count(Item.id),
            ).group_by(Item.inventory_type, Item.required_level, Item.verification_status)
        )
    )
    slots: dict[str, int] = {}
    level_bands = {"unknown": 0}
    level_bands.update({f"{start}-{start + 9}": 0 for start in range(1, 60, 10)})
    verification: dict[str, int] = {}
    for slot, required_level, state, count in rows:
        slots[slot or "unknown"] = slots.get(slot or "unknown", 0) + count
        verification[state] = verification.get(state, 0) + count
        if required_level is None:
            level_bands["unknown"] += count
        else:
            band_start = ((required_level - 1) // 10) * 10 + 1
            band_end = min(band_start + 9, 60)
            band = f"{band_start}-{band_end}"
            level_bands[band] += count
    return {
        "total": sum(slots.values()),
        "by_slot": slots,
        "by_required_level_band": level_bands,
        "by_verification_status": verification,
        "items_with_statistics": session.scalar(
            select(func.count(func.distinct(ItemStat.item_id)))
        ),
        "items_with_acquisition_sources": session.scalar(
            select(func.count(func.distinct(Item.id))).where(Item.acquisitions.any())
        ),
    }


@router.get("/patches", response_model=list[PatchRead])
def list_patches(session: SessionDep) -> list[ForeverPatch]:
    return list(session.scalars(select(ForeverPatch).order_by(ForeverPatch.created_at.desc())))


@router.get("/patches/{patch_id}/imports", response_model=list[ImportSnapshotRead])
def patch_imports(patch_id: int, session: SessionDep) -> list[CatalogImportSnapshot]:
    if session.get(ForeverPatch, patch_id) is None:
        raise HTTPException(status_code=404, detail="Patch not found")
    return list(
        session.scalars(
            select(CatalogImportSnapshot)
            .where(CatalogImportSnapshot.patch_id == patch_id)
            .order_by(CatalogImportSnapshot.started_at.desc())
        )
    )


@router.post("/suggestions", response_model=SuggestionRead, status_code=status.HTTP_201_CREATED)
def create_suggestion(request: SuggestionCreate, session: SessionDep) -> ItemSuggestion:
    profile = session.scalar(
        select(ScoringProfile.id).where(
            ScoringProfile.class_name.ilike(request.class_name),
            ScoringProfile.specialization.ilike(request.specialization),
            ScoringProfile.active.is_(True),
        )
    )
    if profile is None:
        raise HTTPException(status_code=422, detail="Unknown class and specialization context")
    return submit_suggestion(session, request)


@router.get("/suggestions/{suggestion_id}", response_model=SuggestionRead)
def get_suggestion(suggestion_id: UUID, session: SessionDep) -> ItemSuggestion:
    row = session.get(ItemSuggestion, suggestion_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return row
