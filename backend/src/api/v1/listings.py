import uuid
from datetime import timezone, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.models.import_batch import GeocodingStatus, ImportBatch, ImportStatus
from src.models.listing import Listing
from src.schemas.listings import (
    BatchStatusResponse,
    DatasetStatusResponse,
    ImportBatchResponse,
    LatestBatchInfo,
    SkipReason,
)
from src.services.csv_import import CsvImportService
from src.services.geocoding import GeocodingService

router = APIRouter(prefix="/listings", tags=["Listings"])

_csv_import_service = CsvImportService()
_geocoding_service = GeocodingService()


async def _run_geocoding(batch_id: uuid.UUID) -> None:
    from src.db import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        await _geocoding_service.update_listing_coordinates(db, batch_id)


@router.post("/import", status_code=202, response_model=ImportBatchResponse)
async def upload_csv(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        if file.content_type and "csv" not in file.content_type:
            raise HTTPException(
                status_code=400,
                detail={"error": "invalid_file", "message": "File must be a non-empty CSV."},
            )

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_file", "message": "File must be a non-empty CSV."},
        )

    import io

    try:
        parse_result = _csv_import_service.parse(io.BytesIO(contents))
    except ValueError as exc:
        msg = str(exc)
        if "Missing required columns" in msg:
            import re

            cols_match = re.findall(r"'(\w+)'", msg)
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "invalid_schema",
                    "message": "Missing required columns.",
                    "missing_columns": cols_match,
                },
            )
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_file", "message": msg},
        )

    batch = ImportBatch(
        uploaded_at=datetime.now(timezone.utc),
        total_rows=parse_result.total_rows,
        imported_rows=len(parse_result.valid_rows),
        skipped_rows=len(parse_result.skip_reasons),
        skip_reasons=parse_result.skip_reasons or None,
        status=ImportStatus.processing,
        geocoding_status=GeocodingStatus.pending,
    )
    db.add(batch)
    await db.flush()
    await db.refresh(batch)

    await _csv_import_service.bulk_insert(db, batch.id, parse_result.valid_rows)

    batch.status = ImportStatus.completed
    await db.commit()
    await db.refresh(batch)

    background_tasks.add_task(_run_geocoding, batch.id)

    return ImportBatchResponse(
        batch_id=batch.id,
        status=batch.status,
        message=f"Import started. Poll /api/v1/listings/import/{batch.id} for status.",
    )


@router.get("/import/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ImportBatch).where(ImportBatch.id == batch_id))
    batch = result.scalar_one_or_none()
    if batch is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Batch not found."},
        )
    skip_reasons = (
        [SkipReason(**r) for r in batch.skip_reasons] if batch.skip_reasons else None
    )
    return BatchStatusResponse(
        batch_id=batch.id,
        status=batch.status,
        geocoding_status=batch.geocoding_status,
        uploaded_at=batch.uploaded_at,
        total_rows=batch.total_rows,
        imported_rows=batch.imported_rows,
        skipped_rows=batch.skipped_rows,
        skip_reasons=skip_reasons,
    )


@router.get("/status", response_model=DatasetStatusResponse)
async def get_dataset_status(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count()).select_from(Listing))

    latest_batch_result = await db.execute(
        select(ImportBatch)
        .order_by(ImportBatch.uploaded_at.desc())
        .limit(1)
    )
    latest = latest_batch_result.scalar_one_or_none()

    return DatasetStatusResponse(
        total_listings=total or 0,
        last_upload_at=latest.uploaded_at if latest else None,
        latest_batch=(
            LatestBatchInfo(
                batch_id=latest.id,
                imported_rows=latest.imported_rows,
                uploaded_at=latest.uploaded_at,
                geocoding_status=latest.geocoding_status,
            )
            if latest
            else None
        ),
    )
