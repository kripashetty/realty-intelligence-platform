import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


VALID_AMENITIES = {"balcony", "parking", "elevator", "furnished", "garden", "cellar"}


class ApartmentRequest(BaseModel):
    address: str = Field(..., min_length=1)
    size_m2: float = Field(..., ge=5, le=1000)
    rooms: float = Field(..., ge=0.5, le=20)
    floor: int | None = Field(default=None, ge=0, le=50)
    amenities: list[str] | None = None

    def model_post_init(self, __context: object) -> None:
        if self.amenities:
            invalid = set(self.amenities) - VALID_AMENITIES
            if invalid:
                raise ValueError(f"Invalid amenities: {invalid}. Must be one of {VALID_AMENITIES}")


class ConfidenceRange(BaseModel):
    low: float
    high: float


class Factor(BaseModel):
    name: str
    description: str
    value: str

    @field_validator("value", mode="before")
    @classmethod
    def coerce_to_str(cls, v: object) -> str:
        return str(v)


class DataFreshness(BaseModel):
    last_upload_at: datetime | None
    total_listings: int
    is_stale: bool


class RecommendationResponse(BaseModel):
    recommendation_id: uuid.UUID
    recommended_price_eur: float
    confidence_range: ConfidenceRange
    confidence_level: Literal["high", "medium", "low"]
    comparable_count: int
    percentile_rank: float
    explanation: str | None
    factors: list[Factor]
    explanation_available: bool
    data_freshness: DataFreshness
    generated_at: datetime


class NoDataResponse(BaseModel):
    error: str = "no_data"
    message: str
    action: str
