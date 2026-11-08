"""Initial migration checkpoint; the domain schema is intentionally empty.

Revision ID: 20261107_0001
Revises:
Create Date: 2026-11-07
"""

from collections.abc import Sequence

revision: str = "20261107_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Establish migration history without creating game-domain tables."""


def downgrade() -> None:
    """No domain objects were created by this foundation revision."""
