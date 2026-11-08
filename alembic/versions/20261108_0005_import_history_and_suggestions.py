"""Add catalog import snapshots, raw provenance, and community suggestions.

Revision ID: 20261108_0005
Revises: 20261108_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261108_0005"
down_revision: str | None = "20261108_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("items", sa.Column("unique_equip", sa.String(250), nullable=True))
    op.add_column("items", sa.Column("raw_provider_payload", sa.JSON(), nullable=True))
    op.add_column("items", sa.Column("provider_etag", sa.String(500), nullable=True))
    op.add_column("items", sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "items", sa.Column("last_successful_refresh_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "items",
        sa.Column("field_provenance", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "items",
        sa.Column(
            "data_quality_status",
            sa.String(40),
            nullable=False,
            server_default="needs_review",
        ),
    )
    op.create_check_constraint(
        "ck_items_data_quality_status",
        "items",
        "data_quality_status IN ('imported', 'needs_review', 'verified', 'rejected')",
    )

    op.add_column("acquisition_sources", sa.Column("zone_name", sa.String(250), nullable=True))
    op.add_column("acquisition_sources", sa.Column("difficulty", sa.String(120), nullable=True))
    op.add_column(
        "acquisition_sources", sa.Column("faction_requirement", sa.String(80), nullable=True)
    )
    op.add_column("acquisition_sources", sa.Column("conditions", sa.JSON(), nullable=True))
    op.add_column("acquisition_sources", sa.Column("provider_metadata", sa.JSON(), nullable=True))
    op.add_column(
        "acquisition_sources", sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True)
    )

    op.alter_column(
        "forever_patches",
        "status",
        existing_type=sa.String(30),
        server_default="research",
    )
    op.create_check_constraint(
        "ck_forever_patch_status",
        "forever_patches",
        "status IN ('research', 'review', 'published')",
    )

    op.create_table(
        "catalog_import_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("data_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "patch_id",
            sa.Integer(),
            sa.ForeignKey("forever_patches.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("provider_build", sa.String(120), nullable=True),
        sa.Column("provider_etag", sa.String(500), nullable=True),
        sa.Column("search_query", sa.String(64), nullable=True),
        sa.Column("requested_limit", sa.Integer(), nullable=False),
        sa.Column("per_page", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(30), server_default="running", nullable=False),
        sa.Column("fetched_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("imported_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skipped_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("needs_review_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quality_counts", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("resume_state", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("error_summary", sa.String(500), nullable=True),
        sa.CheckConstraint("requested_limit BETWEEN 1 AND 100", name="ck_import_limit_bounded"),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'partial', 'failed')",
            name="ck_import_snapshot_status",
        ),
    )
    op.create_index(
        "ix_catalog_import_snapshots_started_at", "catalog_import_snapshots", ["started_at"]
    )
    op.create_index("ix_catalog_import_snapshots_status", "catalog_import_snapshots", ["status"])

    op.create_table(
        "item_data_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "import_snapshot_id",
            sa.Integer(),
            sa.ForeignKey("catalog_import_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="SET NULL")),
        sa.Column("source_item_id", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(30), nullable=False),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("raw_provider_payload", sa.JSON()),
        sa.Column("normalized_payload", sa.JSON()),
        sa.Column("changed_fields", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("provider_etag", sa.String(500)),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failure_reason", sa.String(500)),
        sa.UniqueConstraint("import_snapshot_id", "source_item_id", name="uq_snapshot_source_item"),
    )
    op.create_index("ix_item_data_snapshots_item_id", "item_data_snapshots", ["item_id"])

    op.create_table(
        "item_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("class_name", sa.String(30), nullable=False),
        sa.Column("specialization", sa.String(50), nullable=False),
        sa.Column("faction", sa.String(20), nullable=False),
        sa.Column("character_level", sa.Integer(), nullable=False),
        sa.Column("equipment_slot", sa.String(30), nullable=False),
        sa.Column("suggested_item_name", sa.String(250), nullable=False),
        sa.Column("wowhead_item_id", sa.Integer(), nullable=False),
        sa.Column("submitted_url", sa.String(500), nullable=False),
        sa.Column("explanation", sa.Text()),
        sa.Column("supporting_evidence", sa.Text()),
        sa.Column("status", sa.String(30), server_default="pending_review", nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "duplicate_of",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("item_suggestions.id", ondelete="SET NULL"),
        ),
        sa.Column("duplicate_flagged", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("reviewer_identity", sa.String(120)),
        sa.Column("reviewer_notes", sa.Text()),
        sa.Column("decision_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("character_level BETWEEN 1 AND 60", name="ck_suggestion_level_range"),
        sa.CheckConstraint("faction IN ('Alliance', 'Horde')", name="ck_suggestion_faction"),
        sa.CheckConstraint(
            "status IN ('pending_review', 'needs_info', 'approved', 'rejected')",
            name="ck_suggestion_status",
        ),
    )
    op.create_index(
        "ix_item_suggestions_status_submitted",
        "item_suggestions",
        ["status", "submitted_at"],
    )
    op.create_index(
        "ix_item_suggestions_item_context",
        "item_suggestions",
        [
            "wowhead_item_id",
            "class_name",
            "specialization",
            "faction",
            "character_level",
            "equipment_slot",
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_item_suggestions_item_context", table_name="item_suggestions")
    op.drop_index("ix_item_suggestions_status_submitted", table_name="item_suggestions")
    op.drop_table("item_suggestions")
    op.drop_index("ix_item_data_snapshots_item_id", table_name="item_data_snapshots")
    op.drop_table("item_data_snapshots")
    op.drop_index("ix_catalog_import_snapshots_status", table_name="catalog_import_snapshots")
    op.drop_index("ix_catalog_import_snapshots_started_at", table_name="catalog_import_snapshots")
    op.drop_table("catalog_import_snapshots")
    op.drop_constraint("ck_forever_patch_status", "forever_patches", type_="check")
    op.alter_column(
        "forever_patches",
        "status",
        existing_type=sa.String(30),
        server_default="draft",
    )
    op.drop_column("acquisition_sources", "captured_at")
    op.drop_column("acquisition_sources", "provider_metadata")
    op.drop_column("acquisition_sources", "conditions")
    op.drop_column("acquisition_sources", "faction_requirement")
    op.drop_column("acquisition_sources", "difficulty")
    op.drop_column("acquisition_sources", "zone_name")
    op.drop_constraint("ck_items_data_quality_status", "items", type_="check")
    op.drop_column("items", "data_quality_status")
    op.drop_column("items", "field_provenance")
    op.drop_column("items", "last_successful_refresh_at")
    op.drop_column("items", "imported_at")
    op.drop_column("items", "provider_etag")
    op.drop_column("items", "raw_provider_payload")
    op.drop_column("items", "unique_equip")
