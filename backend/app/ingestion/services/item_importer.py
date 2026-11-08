"""Bounded, idempotent item import from provider contracts to SQLAlchemy."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.ingestion.normalizers.items import (
    FieldIssue,
    ItemNormalizationError,
    NormalizedItem,
    normalize_item,
)
from backend.app.ingestion.providers.base import ItemProvider
from backend.app.ingestion.providers.thewowdb import ProviderError
from backend.app.models.catalog import (
    DataQualityIssue,
    DataSource,
    GameVersion,
    Item,
    ItemEffect,
    ItemRestriction,
    ItemStat,
)

logger = logging.getLogger(__name__)
MAX_IMPORT_LIMIT = 100


def _issue_dict(issue: FieldIssue, source_item_id: int) -> dict[str, Any]:
    return {
        "source_item_id": source_item_id,
        "field": issue.field_name,
        "code": issue.issue_code,
        "message": issue.message,
        "observed_values": issue.observed_values,
    }


def _upsert_source(session: Session, provider: ItemProvider, checked_at: datetime) -> DataSource:
    source = session.scalar(select(DataSource).where(DataSource.name == provider.name))
    if source is None:
        source = DataSource(
            name=provider.name,
            base_url=provider.base_url,
            terms_url=provider.terms_url,
            attribution_text=provider.attribution_text,
            license_status="permitted_with_attribution",
        )
        session.add(source)
    source.base_url = provider.base_url
    source.terms_url = provider.terms_url
    source.attribution_text = provider.attribution_text
    source.license_status = "permitted_with_attribution"
    source.last_checked_at = checked_at
    session.flush()
    return source


def _get_game_version(
    session: Session, source: DataSource, build: str | None, observed_at: datetime
) -> GameVersion:
    version = session.scalar(
        select(GameVersion).where(
            GameVersion.source_id == source.id,
            GameVersion.game_key == "wow_forever",
            GameVersion.build == build,
        )
    )
    session.query(GameVersion).filter(
        GameVersion.source_id == source.id,
        GameVersion.game_key == "wow_forever",
        GameVersion.is_current.is_(True),
    ).update({GameVersion.is_current: False}, synchronize_session=False)
    if version is None:
        version = GameVersion(
            source_id=source.id,
            game_key="wow_forever",
            build=build,
            observed_at=observed_at,
            is_current=True,
        )
        session.add(version)
        session.flush()
    else:
        version.is_current = True
    return version


def _save_item(
    session: Session,
    source: DataSource,
    normalized: NormalizedItem,
    imported_at: datetime,
) -> str:
    version = _get_game_version(session, source, normalized.build, imported_at)
    item = session.scalar(
        select(Item).where(
            Item.source_id == source.id,
            Item.source_item_id == normalized.source_item_id,
            Item.game_version_id == version.id,
        )
    )
    action = "created" if item is None else "updated"
    if item is None:
        item = Item(
            source_id=source.id,
            source_item_id=normalized.source_item_id,
            game_version_id=version.id,
            name=normalized.name,
            verification_status="provider_reported",
        )
        session.add(item)

    item.name = normalized.name
    item.quality = normalized.quality
    item.item_level = normalized.item_level
    item.required_level = normalized.required_level
    item.inventory_type = normalized.inventory_type
    item.armor_type = normalized.armor_type
    item.weapon_type = normalized.weapon_type
    item.icon_url = normalized.icon_url
    item.source_item_url = normalized.source_item_url
    item.wowhead_url = normalized.wowhead_url
    item.availability_status = "unknown"
    item.verification_status = "needs_review" if normalized.issues else "provider_reported"
    item.updated_at = imported_at
    session.flush()
    item.stats.clear()
    item.effects.clear()
    item.restrictions.clear()
    item.quality_issues.clear()
    session.flush()
    item.stats.extend(
        ItemStat(stat_type=entry.stat_type, value=entry.value) for entry in normalized.stats
    )
    item.effects.extend(
        ItemEffect(
            effect_type=entry.effect_type,
            description=entry.description,
            spell_id=entry.spell_id,
        )
        for entry in normalized.effects
    )
    item.restrictions.extend(
        ItemRestriction(
            restriction_type=entry.restriction_type,
            restriction_value=entry.restriction_value,
            verification_status="provider_reported",
        )
        for entry in normalized.restrictions
    )
    item.quality_issues.extend(
        DataQualityIssue(
            field_name=issue.field_name,
            issue_code=issue.issue_code,
            message=issue.message,
            observed_values=issue.observed_values,
        )
        for issue in normalized.issues
    )
    session.flush()
    return action


def import_items(
    provider: ItemProvider,
    *,
    limit: int,
    session: Session | None = None,
    dry_run: bool = True,
    per_page: int = 100,
) -> dict[str, Any]:
    """Fetch/validate a bounded sample and optionally persist it atomically."""
    if isinstance(limit, bool) or not 1 <= limit <= MAX_IMPORT_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_IMPORT_LIMIT}")
    if not 1 <= per_page <= MAX_IMPORT_LIMIT:
        raise ValueError(f"per_page must be between 1 and {MAX_IMPORT_LIMIT}")
    if not dry_run and session is None:
        raise ValueError("A database session is required when dry_run is false")

    started_at = datetime.now(UTC)
    valid_items: list[NormalizedItem] = []
    failed_records: list[dict[str, Any]] = []
    validation_issues: list[dict[str, Any]] = []
    retrieved = 0

    for summary in provider.iter_item_summaries(limit, per_page=per_page):
        retrieved += 1
        try:
            detail = provider.get_item_detail(summary.id)
            normalized = normalize_item(summary, detail)
            build = detail.build or provider.current_build
            normalized = replace(normalized, build=build)
            valid_items.append(normalized)
            validation_issues.extend(
                _issue_dict(issue, normalized.source_item_id) for issue in normalized.issues
            )
        except (ProviderError, ItemNormalizationError, ValueError) as exc:
            failed_records.append({"source_item_id": summary.id, "reason": str(exc)[:300]})
            logger.warning(
                "Skipping invalid provider item",
                extra={"provider": provider.name, "source_item_id": summary.id},
            )

    created = 0
    updated = 0
    if not dry_run and valid_items:
        assert session is not None
        with session.begin():
            source = _upsert_source(session, provider, datetime.now(UTC))
            for normalized in valid_items:
                action = _save_item(session, source, normalized, datetime.now(UTC))
                if action == "created":
                    created += 1
                else:
                    updated += 1

    report = {
        "provider": provider.name,
        "provider_base_url": provider.base_url,
        "terms_url": provider.terms_url,
        "attribution_required": True,
        "build": provider.current_build,
        "captured_at": started_at.isoformat(),
        "dry_run": dry_run,
        "limit": limit,
        "retrieved": retrieved,
        "validated": len(valid_items),
        "persisted": 0 if dry_run else len(valid_items),
        "created": created,
        "updated": updated,
        "failed_count": len(failed_records),
        "failed_records": failed_records,
        "validation_issue_count": len(validation_issues),
        "validation_issues": validation_issues,
        "wowhead_verified_count": sum(item.wowhead_url is not None for item in valid_items),
    }
    logger.info(
        "Catalog import finished",
        extra={
            "provider": provider.name,
            "retrieved": retrieved,
            "validated": len(valid_items),
            "persisted": report["persisted"],
            "dry_run": dry_run,
        },
    )
    return report
