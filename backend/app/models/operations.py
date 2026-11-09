"""Catalog import history and user-submitted item suggestions."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from backend.app.db.base import Base


class CatalogImportSnapshot(Base):
    """One bounded and resumable provider import run."""

    __tablename__ = "catalog_import_snapshots"
    __table_args__ = (
        CheckConstraint("requested_limit BETWEEN 1 AND 100", name="ck_import_limit_bounded"),
        CheckConstraint(
            "status IN ('running', 'completed', 'partial', 'failed')",
            name="ck_import_snapshot_status",
        ),
        Index("ix_catalog_import_snapshots_started_at", "started_at"),
        Index("ix_catalog_import_snapshots_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id", ondelete="RESTRICT"))
    patch_id: Mapped[int | None] = mapped_column(
        ForeignKey("forever_patches.id", ondelete="RESTRICT")
    )
    provider_build: Mapped[str | None] = mapped_column(String(120))
    provider_etag: Mapped[str | None] = mapped_column(String(500))
    search_query: Mapped[str | None] = mapped_column(String(64))
    requested_limit: Mapped[int] = mapped_column(Integer)
    per_page: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="running", nullable=False)
    fetched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    imported_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    needs_review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_counts: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)
    resume_state: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    error_summary: Mapped[str | None] = mapped_column(String(500))

    records: Mapped[list["ItemDataSnapshot"]] = relationship(
        back_populates="import_snapshot", cascade="all, delete-orphan"
    )


class ItemDataSnapshot(Base):
    """Immutable raw and normalized item observation belonging to an import run."""

    __tablename__ = "item_data_snapshots"
    __table_args__ = (
        UniqueConstraint("import_snapshot_id", "source_item_id", name="uq_snapshot_source_item"),
        Index("ix_item_data_snapshots_item_id", "item_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    import_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_import_snapshots.id", ondelete="CASCADE")
    )
    item_id: Mapped[int | None] = mapped_column(
        ForeignKey("items.id", ondelete="SET NULL"), nullable=True
    )
    source_item_id: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(30))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    raw_provider_payload: Mapped[dict[str, object] | None] = mapped_column(JSON)
    normalized_payload: Mapped[dict[str, object] | None] = mapped_column(JSON)
    changed_fields: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    provider_etag: Mapped[str | None] = mapped_column(String(500))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(String(500))

    import_snapshot: Mapped[CatalogImportSnapshot] = relationship(back_populates="records")


class FullCatalogImportJob(Base):
    """Resumable full-catalog enumeration and hydration run."""

    __tablename__ = "full_catalog_import_jobs"
    __table_args__ = (
        CheckConstraint("per_page BETWEEN 1 AND 100", name="ck_full_catalog_job_page_size"),
        CheckConstraint(
            "status IN ('running', 'enumerated', 'completed', 'partial', 'failed')",
            name="ck_full_catalog_job_status",
        ),
        Index("ix_full_catalog_jobs_status_started", "status", "started_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id", ondelete="RESTRICT"))
    provider_version: Mapped[str] = mapped_column(String(30), default="forever", nullable=False)
    provider_build: Mapped[str | None] = mapped_column(String(120))
    attribution: Mapped[dict[str, object] | None] = mapped_column(JSON)
    per_page: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="running", nullable=False)
    stage: Mapped[str] = mapped_column(String(30), default="enumeration", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_completed_page: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    initial_catalog_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    catalog_items_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    catalog_items_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    catalog_items_unchanged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_prevention_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_pages: Mapped[int | None] = mapped_column(Integer)
    pages_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_ids: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_ids: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invalid_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    http_status_counts: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)
    next_page_url: Mapped[str | None] = mapped_column(String(1000))
    last_etag: Mapped[str | None] = mapped_column(String(500))
    last_error: Mapped[str | None] = mapped_column(String(500))


class FullCatalogImportPage(Base):
    """A provider page is complete only after all valid records have persisted."""

    __tablename__ = "full_catalog_import_pages"
    __table_args__ = (
        UniqueConstraint("job_id", "page_number", name="uq_full_catalog_page_job_number"),
        Index("ix_full_catalog_pages_job_status", "job_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("full_catalog_import_jobs.id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="processing", nullable=False)
    provider_build: Mapped[str | None] = mapped_column(String(120))
    etag: Mapped[str | None] = mapped_column(String(500))
    fetched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invalid_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    response_metadata: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    raw_response_payload: Mapped[dict[str, object] | None] = mapped_column(JSON)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FullCatalogProviderItem(Base):
    """Current provider summary/detail cache for one Forever item ID."""

    __tablename__ = "full_catalog_provider_items"
    __table_args__ = (
        UniqueConstraint(
            "source_id", "provider_version", "provider_item_id", name="uq_full_provider_item"
        ),
        CheckConstraint(
            "hydration_status IN ('pending', 'hydrated', 'not_found', 'failed')",
            name="ck_full_provider_item_hydration_status",
        ),
        Index("ix_full_provider_items_hydration", "hydration_status", "provider_item_id"),
        Index("ix_full_provider_items_build", "provider_build"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("full_catalog_import_jobs.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id", ondelete="RESTRICT"))
    provider_version: Mapped[str] = mapped_column(String(30), default="forever", nullable=False)
    provider_build: Mapped[str | None] = mapped_column(String(120))
    provider_item_id: Mapped[int] = mapped_column(Integer, nullable=False)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("items.id", ondelete="SET NULL"))
    source_page: Mapped[int] = mapped_column(Integer, nullable=False)
    summary_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    summary_validation_error: Mapped[str | None] = mapped_column(String(500))
    summary_etag: Mapped[str | None] = mapped_column(String(500))
    summary_captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detail_payload: Mapped[dict[str, object] | None] = mapped_column(JSON)
    detail_etag: Mapped[str | None] = mapped_column(String(500))
    detail_captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hydration_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    detail_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(500))
    last_http_status: Mapped[int | None] = mapped_column(Integer)


class ItemSuggestion(Base):
    """Public item suggestion; it never mutates catalog or recommendation records."""

    __tablename__ = "item_suggestions"
    __table_args__ = (
        CheckConstraint("character_level BETWEEN 1 AND 60", name="ck_suggestion_level_range"),
        CheckConstraint("faction IN ('Alliance', 'Horde')", name="ck_suggestion_faction"),
        CheckConstraint(
            "status IN ('pending_review', 'needs_info', 'approved', 'rejected')",
            name="ck_suggestion_status",
        ),
        Index("ix_item_suggestions_status_submitted", "status", "submitted_at"),
        Index(
            "ix_item_suggestions_item_context",
            "wowhead_item_id",
            "class_name",
            "specialization",
            "faction",
            "character_level",
            "equipment_slot",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    class_name: Mapped[str] = mapped_column(String(30))
    specialization: Mapped[str] = mapped_column(String(50))
    faction: Mapped[str] = mapped_column(String(20))
    character_level: Mapped[int] = mapped_column(Integer)
    equipment_slot: Mapped[str] = mapped_column(String(30))
    suggested_item_name: Mapped[str] = mapped_column(String(250))
    wowhead_item_id: Mapped[int] = mapped_column(Integer)
    submitted_url: Mapped[str] = mapped_column(String(500))
    explanation: Mapped[str | None] = mapped_column(Text)
    supporting_evidence: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending_review", nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    duplicate_of: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("item_suggestions.id", ondelete="SET NULL")
    )
    duplicate_flagged: Mapped[bool] = mapped_column(default=False, nullable=False)
    reviewer_identity: Mapped[str | None] = mapped_column(String(120))
    reviewer_notes: Mapped[str | None] = mapped_column(Text)
    decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    duplicate_parent: Mapped["ItemSuggestion | None"] = relationship(
        remote_side="ItemSuggestion.id"
    )
