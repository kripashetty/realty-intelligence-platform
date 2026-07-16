import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    Float,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class ConfidenceLevel(enum.StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class PricingRecommendation(Base):
    __tablename__ = "pricing_recommendations"
    __table_args__ = (Index("ix_pricing_recommendations_generated_at", "generated_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    apt_address: Mapped[str] = mapped_column(Text, nullable=False)
    apt_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    apt_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    apt_size_m2: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False)
    apt_rooms: Mapped[float] = mapped_column(Numeric(4, 1), nullable=False)
    apt_floor: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    apt_amenities: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    comparable_count: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_price_eur: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    confidence_low_eur: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    confidence_high_eur: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    percentile_rank: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    factors: Mapped[list] = mapped_column(JSONB, nullable=False)
    comparable_listing_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(10), nullable=False)
