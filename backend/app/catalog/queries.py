"""Database queries for catalog API operations."""

from __future__ import annotations

from typing import Literal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.catalog import DataSource, Item

SortField = Literal["name", "quality", "item_level", "required_level", "updated_at"]


def item_load_options():
    return (
        selectinload(Item.source),
        selectinload(Item.game_version),
        selectinload(Item.stats),
        selectinload(Item.effects),
        selectinload(Item.restrictions),
        selectinload(Item.quality_issues),
    )


def filtered_items(
    *,
    search: str | None = None,
    quality: str | None = None,
    inventory_type: str | None = None,
    min_level: int | None = None,
    max_level: int | None = None,
    source: str | None = None,
    verification_status: str | None = None,
) -> Select[tuple[Item]]:
    statement = select(Item).join(Item.source).join(Item.game_version)
    if search:
        statement = statement.where(Item.name.ilike(f"%{search.strip()}%"))
    if quality:
        if quality.strip().lower() == "unknown":
            statement = statement.where(Item.quality.is_(None))
        else:
            statement = statement.where(func.lower(Item.quality) == quality.strip().lower())
    if inventory_type:
        statement = statement.where(
            func.lower(Item.inventory_type) == inventory_type.strip().lower()
        )
    if min_level is not None:
        statement = statement.where(Item.required_level >= min_level)
    if max_level is not None:
        statement = statement.where(Item.required_level <= max_level)
    if source:
        statement = statement.where(func.lower(DataSource.name) == source.strip().lower())
    if verification_status:
        statement = statement.where(Item.verification_status == verification_status)
    return statement


def list_items(
    session: Session,
    *,
    page: int,
    page_size: int,
    sort_by: SortField,
    sort_order: Literal["asc", "desc"],
    **filters: str | int | None,
) -> tuple[list[Item], int]:
    base = filtered_items(**filters)
    total = session.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0
    sort_column = getattr(Item, sort_by)
    order = sort_column.asc().nullslast() if sort_order == "asc" else sort_column.desc().nullslast()
    rows = session.scalars(
        base.options(*item_load_options())
        .order_by(order, Item.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total


def get_item(session: Session, item_id: int) -> Item | None:
    return session.scalar(select(Item).where(Item.id == item_id).options(*item_load_options()))


def catalog_summary(session: Session) -> dict[str, object]:
    total = session.scalar(select(func.count(Item.id))) or 0
    qualities = session.execute(
        select(Item.quality, func.count(Item.id)).group_by(Item.quality).order_by(Item.quality)
    ).all()
    statuses = session.execute(
        select(Item.verification_status, func.count(Item.id))
        .group_by(Item.verification_status)
        .order_by(Item.verification_status)
    ).all()
    inventory_types = session.scalars(
        select(Item.inventory_type)
        .where(Item.inventory_type.is_not(None))
        .distinct()
        .order_by(Item.inventory_type)
    ).all()
    last_import = session.scalar(select(func.max(DataSource.last_checked_at)))
    sources = session.scalars(
        select(DataSource).where(DataSource.last_checked_at.is_not(None)).order_by(DataSource.name)
    ).all()
    return {
        "total_items": total,
        "items_by_quality": [
            {"quality": quality or "unknown", "count": count} for quality, count in qualities
        ],
        "items_by_verification_status": [
            {"verification_status": status, "count": count} for status, count in statuses
        ],
        "inventory_types": inventory_types,
        "last_import_at": last_import,
        "active_data_sources": sources,
    }
