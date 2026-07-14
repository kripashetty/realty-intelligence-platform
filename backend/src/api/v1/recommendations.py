import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.models.import_batch import ImportBatch
from src.models.listing import Listing
from src.models.recommendation import ConfidenceLevel, PricingRecommendation
from src.schemas.recommendations import (
    ApartmentRequest,
    ConfidenceRange,
    DataFreshness,
    Factor,
    RecommendationResponse,
)
from src.services.comparables import ComparablesService
from src.services.explanation import ExplanationService
from src.services.geocoding import GeocodingService
from src.services.pricing import PricingService

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

_geocoding = GeocodingService()
_comparables = ComparablesService()
_pricing = PricingService()
_explanation = ExplanationService(
    ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434")
)

_STALE_HOURS = 48


@router.post("", response_model=RecommendationResponse)
async def get_recommendation(
    request: ApartmentRequest,
    db: AsyncSession = Depends(get_db),
):
    # Check data availability
    total = await db.scalar(select(func.count()).select_from(Listing))
    if not total:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "no_data",
                "message": "No listing data available. Please upload a CSV first.",
                "action": "Upload a Fredy CSV export at POST /api/v1/listings/import",
            },
        )

    # Geocode apartment address
    apt_lat, apt_lng = await _geocoding.geocode(request.address)

    # Find comparables
    if apt_lat is not None and apt_lng is not None:
        comparables = await _comparables.find_comparables(
            db, lat=apt_lat, lng=apt_lng, size_m2=request.size_m2, rooms=request.rooms
        )
    else:
        comparables = await _comparables.find_comparables_no_geo(
            db, size_m2=request.size_m2, rooms=request.rooms
        )

    if not comparables:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "no_data",
                "message": "No comparable listings found for this apartment.",
                "action": "Upload more listing data or broaden the search area.",
            },
        )

    # Statistical pricing
    pricing = _pricing.calculate(comparables)

    # Data freshness
    latest_batch_result = await db.execute(
        select(ImportBatch).order_by(ImportBatch.uploaded_at.desc()).limit(1)
    )
    latest_batch = latest_batch_result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    is_stale = (
        latest_batch is None
        or (now - latest_batch.uploaded_at) > timedelta(hours=_STALE_HOURS)
    )

    # LLM explanation
    stats = {
        "comparable_count": pricing.comparable_count,
        "recommended_price_eur": pricing.recommended_price_eur,
        "confidence_low_eur": pricing.confidence_low_eur,
        "confidence_high_eur": pricing.confidence_high_eur,
        "percentile_rank": pricing.percentile_rank,
    }
    explanation_result = await _explanation.generate(
        apartment=request.model_dump(), stats=stats
    )

    # Persist recommendation
    comparable_ids = [str(c.id) for c in comparables]
    factors_data = explanation_result.factors if explanation_result.explanation_available else []

    rec = PricingRecommendation(
        generated_at=now,
        import_batch_id=latest_batch.id if latest_batch else uuid.uuid4(),
        apt_address=request.address,
        apt_latitude=apt_lat,
        apt_longitude=apt_lng,
        apt_size_m2=request.size_m2,
        apt_rooms=request.rooms,
        apt_floor=request.floor,
        apt_amenities=request.amenities,
        comparable_count=pricing.comparable_count,
        recommended_price_eur=pricing.recommended_price_eur,
        confidence_low_eur=pricing.confidence_low_eur,
        confidence_high_eur=pricing.confidence_high_eur,
        percentile_rank=pricing.percentile_rank,
        explanation=explanation_result.explanation,
        factors=factors_data,
        comparable_listing_ids=comparable_ids,
        confidence_level=pricing.confidence_level,
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)

    return RecommendationResponse(
        recommendation_id=rec.id,
        recommended_price_eur=float(pricing.recommended_price_eur),
        confidence_range=ConfidenceRange(
            low=float(pricing.confidence_low_eur),
            high=float(pricing.confidence_high_eur),
        ),
        confidence_level=pricing.confidence_level,
        comparable_count=pricing.comparable_count,
        percentile_rank=pricing.percentile_rank,
        explanation=explanation_result.explanation,
        factors=[Factor(**f) for f in factors_data],
        explanation_available=explanation_result.explanation_available,
        data_freshness=DataFreshness(
            last_upload_at=latest_batch.uploaded_at if latest_batch else None,
            total_listings=total or 0,
            is_stale=is_stale,
        ),
        generated_at=now,
    )
