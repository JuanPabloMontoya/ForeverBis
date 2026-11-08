"""Create the versioned provider-backed Forever item catalog.

Revision ID: 20261107_0002
Revises: 20261107_0001
Create Date: 2026-11-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261107_0002"
down_revision: str | None = "20261107_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "data_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("base_url", sa.String(length=300), nullable=False),
        sa.Column("terms_url", sa.String(length=500), nullable=False),
        sa.Column("attribution_text", sa.String(length=300), nullable=False),
        sa.Column("license_status", sa.String(length=80), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_data_sources_name", "data_sources", ["name"], unique=False)

    op.create_table(
        "game_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_key", sa.String(length=80), nullable=False),
        sa.Column("build", sa.String(length=120), nullable=True),
        sa.Column(
            "observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "source_id", "game_key", "build", name="uq_game_version_source_key_build"
        ),
    )
    op.create_index("ix_game_versions_game_key", "game_versions", ["game_key"], unique=False)
    op.create_index(
        "uq_game_version_current_per_source_key",
        "game_versions",
        ["source_id", "game_key"],
        unique=True,
        postgresql_where=sa.text("is_current IS TRUE"),
    )

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("source_item_id", sa.Integer(), nullable=False),
        sa.Column("game_version_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("quality", sa.String(length=40), nullable=True),
        sa.Column("item_level", sa.Integer(), nullable=True),
        sa.Column("required_level", sa.Integer(), nullable=True),
        sa.Column("inventory_type", sa.String(length=80), nullable=True),
        sa.Column("armor_type", sa.String(length=80), nullable=True),
        sa.Column("weapon_type", sa.String(length=100), nullable=True),
        sa.Column("icon_url", sa.String(length=1000), nullable=True),
        sa.Column("source_item_url", sa.String(length=1000), nullable=True),
        sa.Column("wowhead_url", sa.String(length=1000), nullable=True),
        sa.Column(
            "availability_status", sa.String(length=40), nullable=False, server_default="unknown"
        ),
        sa.Column("verification_status", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("source_item_id > 0", name="ck_item_source_item_id_positive"),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["game_version_id"], ["game_versions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "source_id", "source_item_id", "game_version_id", name="uq_item_source_version_id"
        ),
    )
    for index_name, columns in (
        ("ix_items_name", ["name"]),
        ("ix_items_quality", ["quality"]),
        ("ix_items_verification_status", ["verification_status"]),
        ("ix_items_game_version_id", ["game_version_id"]),
        ("ix_items_quality_required_level", ["quality", "required_level"]),
        ("ix_items_inventory_type", ["inventory_type"]),
    ):
        op.create_index(index_name, "items", columns, unique=False)

    op.create_table(
        "item_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("stat_type", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_item_stats_item_id", "item_stats", ["item_id"], unique=False)
    op.create_index(
        "ix_item_stats_item_stat_type", "item_stats", ["item_id", "stat_type"], unique=False
    )

    op.create_table(
        "item_effects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("effect_type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("spell_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_item_effects_item_id", "item_effects", ["item_id"], unique=False)

    op.create_table(
        "item_restrictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("restriction_type", sa.String(length=80), nullable=False),
        sa.Column("restriction_value", sa.String(length=200), nullable=False),
        sa.Column("verification_status", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_item_restrictions_item_id", "item_restrictions", ["item_id"], unique=False)
    op.create_index(
        "ix_item_restrictions_type_value",
        "item_restrictions",
        ["restriction_type", "restriction_value"],
        unique=False,
    )

    op.create_table(
        "data_quality_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("issue_code", sa.String(length=100), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("observed_values", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("item_id", "field_name", "issue_code", name="uq_item_quality_issue"),
    )
    op.create_index(
        "ix_data_quality_issues_item_id", "data_quality_issues", ["item_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_data_quality_issues_item_id", table_name="data_quality_issues")
    op.drop_table("data_quality_issues")
    op.drop_index("ix_item_restrictions_type_value", table_name="item_restrictions")
    op.drop_index("ix_item_restrictions_item_id", table_name="item_restrictions")
    op.drop_table("item_restrictions")
    op.drop_index("ix_item_effects_item_id", table_name="item_effects")
    op.drop_table("item_effects")
    op.drop_index("ix_item_stats_item_stat_type", table_name="item_stats")
    op.drop_index("ix_item_stats_item_id", table_name="item_stats")
    op.drop_table("item_stats")
    for index_name in (
        "ix_items_inventory_type",
        "ix_items_quality_required_level",
        "ix_items_game_version_id",
        "ix_items_verification_status",
        "ix_items_quality",
        "ix_items_name",
    ):
        op.drop_index(index_name, table_name="items")
    op.drop_table("items")
    op.drop_index("uq_game_version_current_per_source_key", table_name="game_versions")
    op.drop_index("ix_game_versions_game_key", table_name="game_versions")
    op.drop_table("game_versions")
    op.drop_index("ix_data_sources_name", table_name="data_sources")
    op.drop_table("data_sources")
