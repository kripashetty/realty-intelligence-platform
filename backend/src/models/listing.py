import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, Index, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint("source_url", "listing_date", name="uq_listing_source_url_date"),
        Index("ix_listing_lat_lng", "latitude", "longitude"),
        Index("ix_listing_price_eur", "price_eur"),
        Index("ix_listing_size_rooms", "size_m2", "rooms"),
        Index("ix_listing_date", "listing_date"),
        Index("ix_listing_batch_id", "import_batch_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    import_batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_eur: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    size_m2: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False)
    rooms: Mapped[float] = mapped_column(Numeric(4, 1), nullable=False)
    floor: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    platform: Mapped[str] = mapped_column(String(100), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    listing_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
