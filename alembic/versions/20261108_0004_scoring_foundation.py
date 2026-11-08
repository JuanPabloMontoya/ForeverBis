"""Add scoring profiles, eligibility completeness, and internal patch foundation.

Revision ID: 20261108_0004
Revises: 20261107_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261108_0004"
down_revision: str | None = "20261107_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CLASSES = {
    "Druid": ["Balance", "Feral", "Restoration"],
    "Hunter": ["Beast Mastery", "Marksmanship", "Survival"],
    "Mage": ["Arcane", "Fire", "Frost"],
    "Paladin": ["Holy", "Protection", "Retribution"],
    "Priest": ["Discipline", "Holy", "Shadow"],
    "Rogue": ["Assassination", "Combat", "Subtlety"],
    "Shaman": ["Elemental", "Enhancement", "Restoration"],
    "Warlock": ["Affliction", "Demonology", "Destruction"],
    "Warrior": ["Arms", "Fury", "Protection"],
}


def upgrade() -> None:
    op.create_table(
        "forever_patches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patch_key", sa.String(80), nullable=False, unique=True),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.add_column("game_versions", sa.Column("patch_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_game_versions_patch_id_forever_patches",
        "game_versions",
        "forever_patches",
        ["patch_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.add_column("items", sa.Column("armor_value", sa.Numeric(12, 3), nullable=True))
    op.add_column("items", sa.Column("weapon_damage_min", sa.Numeric(12, 3), nullable=True))
    op.add_column("items", sa.Column("weapon_damage_max", sa.Numeric(12, 3), nullable=True))
    op.add_column("items", sa.Column("weapon_speed", sa.Numeric(12, 3), nullable=True))
    op.add_column(
        "items",
        sa.Column("eligibility_status", sa.String(40), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "items",
        sa.Column("statistics_status", sa.String(40), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "items", sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True)
    )

    op.create_table(
        "scoring_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_name", sa.String(30), nullable=False),
        sa.Column("specialization", sa.String(50), nullable=False),
        sa.Column("role", sa.String(30), nullable=True),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("provisional", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("assumptions", sa.Text(), nullable=False),
        sa.Column("stat_weights", sa.JSON(), nullable=False),
        sa.Column("adjustments", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "class_name", "specialization", "version", name="uq_scoring_profile_class_spec_version"
        ),
    )
    op.create_index("ix_scoring_profiles_class_name", "scoring_profiles", ["class_name"])
    op.create_index(
        "uq_scoring_profile_active_class_spec",
        "scoring_profiles",
        ["class_name", "specialization"],
        unique=True,
        postgresql_where=sa.text("active IS TRUE"),
        sqlite_where=sa.text("active = 1"),
    )
    op.create_table(
        "class_capability_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_name", sa.String(30), nullable=False),
        sa.Column("ruleset_key", sa.String(50), nullable=False, server_default="wow_forever"),
        sa.Column("verification_status", sa.String(40), nullable=False, server_default="unknown"),
        sa.Column("armor_types", sa.JSON(), nullable=True),
        sa.Column("weapon_types", sa.JSON(), nullable=True),
        sa.UniqueConstraint("class_name", "ruleset_key", name="uq_class_capability_ruleset"),
    )
    op.create_table(
        "acquisition_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("name", sa.String(250), nullable=True),
        sa.Column("external_id", sa.String(120), nullable=True),
        sa.Column("location", sa.String(250), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("game_version_id", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("verification_status", sa.String(40), nullable=False, server_default="unknown"),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["game_version_id"], ["game_versions.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_acquisition_sources_type_name", "acquisition_sources", ["source_type", "name"]
    )
    op.create_table(
        "item_acquisitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("acquisition_source_id", sa.Integer(), nullable=False),
        sa.Column("verification_status", sa.String(40), nullable=False, server_default="unknown"),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["acquisition_source_id"], ["acquisition_sources.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("item_id", "acquisition_source_id", name="uq_item_acquisition_source"),
    )
    op.create_index("ix_item_acquisitions_item_id", "item_acquisitions", ["item_id"])

    assumptions = (
        "No validated WoW Forever specialization weights are available. "
        "Weights are intentionally empty; configure only with documented evidence."
    )
    for class_name, specializations in CLASSES.items():
        for spec in specializations:
            # JSONB-compatible PostgreSQL literals also keep `alembic upgrade --sql` usable.
            op.execute(
                sa.text(
                    "INSERT INTO scoring_profiles "
                    "(class_name, specialization, role, version, active, provisional, "
                    "assumptions, stat_weights, adjustments) "
                    f"VALUES ('{class_name}', '{spec}', NULL, 'v1-provisional', TRUE, TRUE, "
                    f"'{assumptions}', '{{}}'::json, '{{}}'::json)"
                )
            )
    for class_name in CLASSES:
        op.execute(
            sa.text(
                "INSERT INTO class_capability_profiles "
                "(class_name, ruleset_key, verification_status, armor_types, weapon_types) "
                f"VALUES ('{class_name}', 'wow_forever', 'unknown', NULL, NULL)"
            )
        )


def downgrade() -> None:
    op.drop_index("ix_item_acquisitions_item_id", table_name="item_acquisitions")
    op.drop_table("item_acquisitions")
    op.drop_index("ix_acquisition_sources_type_name", table_name="acquisition_sources")
    op.drop_table("acquisition_sources")
    op.drop_table("class_capability_profiles")
    op.drop_index("ix_scoring_profiles_class_name", table_name="scoring_profiles")
    op.drop_index("uq_scoring_profile_active_class_spec", table_name="scoring_profiles")
    op.drop_table("scoring_profiles")
    op.drop_column("items", "last_validated_at")
    op.drop_column("items", "statistics_status")
    op.drop_column("items", "eligibility_status")
    op.drop_column("items", "weapon_speed")
    op.drop_column("items", "weapon_damage_max")
    op.drop_column("items", "weapon_damage_min")
    op.drop_column("items", "armor_value")
    op.drop_constraint(
        "fk_game_versions_patch_id_forever_patches", "game_versions", type_="foreignkey"
    )
    op.drop_column("game_versions", "patch_id")
    op.drop_table("forever_patches")
