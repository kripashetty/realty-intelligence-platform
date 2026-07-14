import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class ImportStatus(str, enum.Enum):
    processing = "processing"
    completed = "completed"
    failed = "failed"


class GeocodingStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class ImportBatch(Base):
    __tablename__ = "import_batches"
    __table_args__ = (Index("ix_import_batches_uploaded_at", "uploaded_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skip_reasons: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ImportStatus.processing)
    geocoding_status: Mapped[str] = mapped_column(String(20), nullable=False, default=GeocodingStatus.pending)
