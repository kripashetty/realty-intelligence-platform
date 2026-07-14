"""T032 — Unit tests for pricing service.

Written before implementation (TDD red phase).
src.services.pricing does not exist yet.
"""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.services.pricing import PricingService


def _make_listing(price: float):
    m = MagicMock()
    m.price_eur = Decimal(str(price))
    return m


class TestPricingService:
    @pytest.fixture
    def service(self):
        return PricingService()

    def test_median_price_is_recommended(self, service):
        listings = [_make_listing(p) for p in [1000, 1200, 1400, 1600, 1800]]
        result = service.calculate(listings)
        assert result.recommended_price_eur == pytest.approx(Decimal("1400.00"), abs=Decimal("0.01"))

    def test_confidence_range_is_25th_75th_percentile(self, service):
        listings = [_make_listing(p) for p in [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700]]
        result = service.calculate(listings)
        assert result.confidence_low_eur <= result.recommended_price_eur
        assert result.confidence_high_eur >= result.recommended_price_eur

    def test_confidence_level_high_when_10_or_more_comparables(self, service):
        listings = [_make_listing(1200) for _ in range(10)]
        result = service.calculate(listings)
        assert result.confidence_level == "high"

    def test_confidence_level_medium_when_5_to_9_comparables(self, service):
        listings = [_make_listing(1200) for _ in range(7)]
        result = service.calculate(listings)
        assert result.confidence_level == "medium"

    def test_confidence_level_low_when_fewer_than_5_comparables(self, service):
        listings = [_make_listing(1200) for _ in range(3)]
        result = service.calculate(listings)
        assert result.confidence_level == "low"

    def test_percentile_rank_is_0_to_100(self, service):
        listings = [_make_listing(p) for p in [1000, 1200, 1400, 1600, 1800]]
        result = service.calculate(listings)
        assert 0.0 <= result.percentile_rank <= 100.0

    def test_comparable_count_matches_input_length(self, service):
        listings = [_make_listing(1200) for _ in range(15)]
        result = service.calculate(listings)
        assert result.comparable_count == 15

    def test_raises_when_no_comparables(self, service):
        with pytest.raises(ValueError, match="comparable"):
            service.calculate([])
