"""SQLAlchemy metadata base; domain tables are intentionally not defined yet."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base for future persistence models."""
