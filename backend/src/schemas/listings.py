import uuid
from datetime import datetime

from pydantic import BaseModel


class ImportBatchResponse(BaseModel):
    batch_id: uuid.UUID
    status: str
    message: str


class SkipReason(BaseModel):
    row_number: int
    reason: str


class BatchStatusResponse(BaseModel):
    batch_id: uuid.UUID
    status: str
    geocoding_status: str
    uploaded_at: datetime
    total_rows: int
    imported_rows: int
    skipped_rows: int
    skip_reasons: list[SkipReason] | None = None


class LatestBatchInfo(BaseModel):
    batch_id: uuid.UUID
    imported_rows: int
    uploaded_at: datetime
    geocoding_status: str


class DatasetStatusResponse(BaseModel):
    total_listings: int
    last_upload_at: datetime | None
    latest_batch: LatestBatchInfo | None
