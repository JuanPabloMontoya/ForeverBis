"""Provider provenance and normalized Forever item catalog models."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    base_url: Mapped[str] = mapped_column(String(300))
    terms_url: Mapped[str] = mapped_column(String(500))
    attribution_text: Mapped[str] = mapped_column(String(300))
    license_status: Mapped[str] = mapped_column(String(80))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    game_versions: Mapped[list["GameVersion"]] = relationship(back_populates="source")
    items: Mapped[list["Item"]] = relationship(back_populates="source")


class GameVersion(Base):
    __tablename__ = "game_versions"
    __table_args__ = (
        UniqueConstraint("source_id", "game_key", "build", name="uq_game_version_source_key_build"),
        Index(
            "uq_game_version_current_per_source_key",
            "source_id",
            "game_key",
            unique=True,
            postgresql_where=text("is_current IS TRUE"),
            sqlite_where=text("is_current = 1"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_key: Mapped[str] = mapped_column(String(80), index=True)
    build: Mapped[str | None] = mapped_column(String(120))
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id", ondelete="RESTRICT"))
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    source: Mapped[DataSource] = relationship(back_populates="game_versions")
    items: Mapped[list["Item"]] = relationship(back_populates="game_version")


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        UniqueConstraint(
            "source_id", "source_item_id", "game_version_id", name="uq_item_source_version_id"
        ),
        CheckConstraint("source_item_id > 0", name="ck_item_source_item_id_positive"),
        Index("ix_items_quality_required_level", "quality", "required_level"),
        Index("ix_items_inventory_type", "inventory_type"),
        Index("ix_items_verification_status", "verification_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id", ondelete="RESTRICT"))
    source_item_id: Mapped[int] = mapped_column(Integer)
    game_version_id: Mapped[int] = mapped_column(
        ForeignKey("game_versions.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(250), index=True)
    quality: Mapped[str | None] = mapped_column(String(40), index=True)
    item_level: Mapped[int | None] = mapped_column(Integer)
    required_level: Mapped[int | None] = mapped_column(Integer)
    inventory_type: Mapped[str | None] = mapped_column(String(80))
    armor_type: Mapped[str | None] = mapped_column(String(80))
    weapon_type: Mapped[str | None] = mapped_column(String(100))
    icon_url: Mapped[str | None] = mapped_column(String(1000))
    source_item_url: Mapped[str | None] = mapped_column(String(1000))
    wowhead_url: Mapped[str | None] = mapped_column(String(1000))
    availability_status: Mapped[str] = mapped_column(String(40), default="unknown")
    verification_status: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    source: Mapped[DataSource] = relationship(back_populates="items")
    game_version: Mapped[GameVersion] = relationship(back_populates="items")
    stats: Mapped[list["ItemStat"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="ItemStat.id"
    )
    effects: Mapped[list["ItemEffect"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="ItemEffect.id"
    )
    restrictions: Mapped[list["ItemRestriction"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="ItemRestriction.id"
    )
    quality_issues: Mapped[list["DataQualityIssue"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="DataQualityIssue.id"
    )


class ItemStat(Base):
    __tablename__ = "item_stats"
    __table_args__ = (Index("ix_item_stats_item_stat_type", "item_id", "stat_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    stat_type: Mapped[str] = mapped_column(String(100))
    value: Mapped[Decimal] = mapped_column(Numeric(12, 3))

    item: Mapped[Item] = relationship(back_populates="stats")


class ItemEffect(Base):
    __tablename__ = "item_effects"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    effect_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    spell_id: Mapped[int | None] = mapped_column(Integer)

    item: Mapped[Item] = relationship(back_populates="effects")


class ItemRestriction(Base):
    __tablename__ = "item_restrictions"
    __table_args__ = (
        Index("ix_item_restrictions_type_value", "restriction_type", "restriction_value"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    restriction_type: Mapped[str] = mapped_column(String(80))
    restriction_value: Mapped[str] = mapped_column(String(200))
    verification_status: Mapped[str] = mapped_column(String(40))

    item: Mapped[Item] = relationship(back_populates="restrictions")


class DataQualityIssue(Base):
    """Field-level discrepancy/uncertainty retained without asserting a value."""

    __tablename__ = "data_quality_issues"
    __table_args__ = (
        UniqueConstraint("item_id", "field_name", "issue_code", name="uq_item_quality_issue"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    field_name: Mapped[str] = mapped_column(String(100))
    issue_code: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(String(500))
    observed_values: Mapped[dict[str, object] | list[object] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    item: Mapped[Item] = relationship(back_populates="quality_issues")
