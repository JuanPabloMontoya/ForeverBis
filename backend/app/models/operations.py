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
