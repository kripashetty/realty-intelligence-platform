import statistics
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

import numpy as np
import scipy.stats

if TYPE_CHECKING:
    from src.models.listing import Listing


@dataclass
class PricingResult:
    recommended_price_eur: Decimal
    confidence_low_eur: Decimal
    confidence_high_eur: Decimal
    confidence_level: str
    percentile_rank: float
    comparable_count: int


def _confidence_level(count: int) -> str:
    if count >= 10:
        return "high"
    if count >= 5:
        return "medium"
    return "low"


class PricingService:
    def calculate(self, listings: list) -> PricingResult:
        if not listings:
            raise ValueError("No comparable listings provided")

        prices = [float(l.price_eur) for l in listings]
        median = statistics.median(prices)
        low = float(np.percentile(prices, 25))
        high = float(np.percentile(prices, 75))
        rank = float(scipy.stats.percentileofscore(prices, median, kind="rank"))

        return PricingResult(
            recommended_price_eur=Decimal(str(round(median, 2))),
            confidence_low_eur=Decimal(str(round(low, 2))),
            confidence_high_eur=Decimal(str(round(high, 2))),
            confidence_level=_confidence_level(len(listings)),
            percentile_rank=round(rank, 1),
            comparable_count=len(listings),
        )
