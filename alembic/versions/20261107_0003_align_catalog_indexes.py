"""Align provider table indexes with the mapped catalog metadata.

Revision ID: 20261107_0003
Revises: 20261107_0002
Create Date: 2026-11-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261107_0003"
down_revision: str | None = "20261107_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # The unique constraint already indexes this field in PostgreSQL.
    op.drop_index("ix_data_sources_name", table_name="data_sources")


def downgrade() -> None:
    op.create_index("ix_data_sources_name", "data_sources", ["name"], unique=False)
