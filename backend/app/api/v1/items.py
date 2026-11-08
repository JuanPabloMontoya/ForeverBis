"""Read-only HTTP API for the imported Forever item catalog."""

from __future__ import annotations

from math import ceil
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.catalog.queries import catalog_summary, get_item, list_items
from backend.app.db.session import get_session
from backend.app.schemas.catalog import CatalogItemRead, CatalogPage, CatalogSummary

router = APIRouter(tags=["catalog"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/items", response_model=CatalogPage[CatalogItemRead])
def read_items(
    session: SessionDep,
    search: Annotated[str | None, Query(max_length=100)] = None,
    quality: Annotated[str | None, Query(max_length=40)] = None,
    inventory_type: Annotated[str | None, Query(max_length=80)] = None,
    min_level: Annotated[int | None, Query(ge=0, le=100)] = None,
    max_level: Annotated[int | None, Query(ge=0, le=100)] = None,
    source: Annotated[str | None, Query(max_length=100)] = None,
    verification_status: Annotated[str | None, Query(max_length=40)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 24,
    sort_by: Literal["name", "quality", "item_level", "required_level", "updated_at"] = "name",
    sort_order: Literal["asc", "desc"] = "asc",
) -> CatalogPage[CatalogItemRead]:
    if min_level is not None and max_level is not None and min_level > max_level:
        raise HTTPException(status_code=422, detail="min_level must not exceed max_level")
    rows, total = list_items(
        session,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        quality=quality,
        inventory_type=inventory_type,
        min_level=min_level,
        max_level=max_level,
        source=source,
        verification_status=verification_status,
    )
    return CatalogPage[CatalogItemRead](
        items=rows,
        page=page,
        page_size=page_size,
        total=total,
        pages=ceil(total / page_size),
    )


@router.get("/items/{item_id}", response_model=CatalogItemRead)
def read_item(item_id: int, session: SessionDep) -> CatalogItemRead:
    item = get_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Catalog item not found")
    return CatalogItemRead.model_validate(item)


@router.get("/catalog/summary", response_model=CatalogSummary)
def read_catalog_summary(session: SessionDep) -> CatalogSummary:
    return CatalogSummary.model_validate(catalog_summary(session))
