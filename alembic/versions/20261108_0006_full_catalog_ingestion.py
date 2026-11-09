"""Add resumable full-catalog enumeration and item hydration state.

Revision ID: 20261108_0006
Revises: 20261108_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261108_0006"
down_revision: str | None = "20261108_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "full_catalog_import_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("data_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("provider_version", sa.String(30), nullable=False, server_default="forever"),
        sa.Column("provider_build", sa.String(120)),
        sa.Column("attribution", sa.JSON()),
        sa.Column("per_page", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("status", sa.String(30), nullable=False, server_default="running"),
        sa.Column("stage", sa.String(30), nullable=False, server_default="enumeration"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("last_completed_page", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("initial_catalog_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("catalog_items_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("catalog_items_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("catalog_items_unchanged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_prevention_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_pages", sa.Integer()),
        sa.Column("pages_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_ids", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_ids", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("http_status_counts", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("next_page_url", sa.String(1000)),
        sa.Column("last_etag", sa.String(500)),
        sa.Column("last_error", sa.String(500)),
        sa.CheckConstraint("per_page BETWEEN 1 AND 100", name="ck_full_catalog_job_page_size"),
        sa.CheckConstraint(
            "status IN ('running', 'enumerated', 'completed', 'partial', 'failed')",
            name="ck_full_catalog_job_status",
        ),
    )
    op.create_index(
        "ix_full_catalog_jobs_status_started", "full_catalog_import_jobs", ["status", "started_at"]
    )

    op.create_table(
        "full_catalog_import_pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("full_catalog_import_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="processing"),
        sa.Column("provider_build", sa.String(120)),
        sa.Column("etag", sa.String(500)),
        sa.Column("fetched_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("response_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("raw_response_payload", sa.JSON()),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("job_id", "page_number", name="uq_full_catalog_page_job_number"),
    )
    op.create_index(
        "ix_full_catalog_pages_job_status", "full_catalog_import_pages", ["job_id", "status"]
    )

    op.create_table(
        "full_catalog_provider_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("full_catalog_import_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("data_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("provider_version", sa.String(30), nullable=False, server_default="forever"),
        sa.Column("provider_build", sa.String(120)),
        sa.Column("provider_item_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="SET NULL")),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.Column("summary_payload", sa.JSON(), nullable=False),
        sa.Column("summary_validation_error", sa.String(500)),
        sa.Column("summary_etag", sa.String(500)),
        sa.Column("summary_captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detail_payload", sa.JSON()),
        sa.Column("detail_etag", sa.String(500)),
        sa.Column("detail_captured_at", sa.DateTime(timezone=True)),
        sa.Column("hydration_status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("detail_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(500)),
        sa.Column("last_http_status", sa.Integer()),
        sa.UniqueConstraint(
            "source_id", "provider_version", "provider_item_id", name="uq_full_provider_item"
        ),
        sa.CheckConstraint(
            "hydration_status IN ('pending', 'hydrated', 'not_found', 'failed')",
            name="ck_full_provider_item_hydration_status",
        ),
    )
    op.create_index(
        "ix_full_provider_items_hydration",
        "full_catalog_provider_items",
        ["hydration_status", "provider_item_id"],
    )
    op.create_index(
        "ix_full_provider_items_build", "full_catalog_provider_items", ["provider_build"]
    )


def downgrade() -> None:
    op.drop_index("ix_full_provider_items_build", table_name="full_catalog_provider_items")
    op.drop_index("ix_full_provider_items_hydration", table_name="full_catalog_provider_items")
    op.drop_table("full_catalog_provider_items")
    op.drop_index("ix_full_catalog_pages_job_status", table_name="full_catalog_import_pages")
    op.drop_table("full_catalog_import_pages")
    op.drop_index("ix_full_catalog_jobs_status_started", table_name="full_catalog_import_jobs")
    op.drop_table("full_catalog_import_jobs")
