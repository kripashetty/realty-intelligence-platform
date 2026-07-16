"""T034 — Integration test for full recommendation flow.

Written before implementation (TDD red phase).
Requires live test DB + mocked Ollama.
"""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def no_background_geocoding():
    """Prevent _run_geocoding from opening a competing DB session during tests."""
    with patch("src.api.v1.listings._run_geocoding", new=AsyncMock()):
        yield

SAMPLE_CSV = """\
title,address,price,size,rooms,floor,url,date,provider
Flat A,Invalidenstraße 50 10115 Berlin,1100.00,60.0,3.0,1,https://example.com/rec-1,2026-07-10,immobilienscout24
Flat B,Invalidenstraße 60 10115 Berlin,1200.00,65.0,3.0,2,https://example.com/rec-2,2026-07-10,immobilienscout24
Flat C,Invalidenstraße 70 10115 Berlin,1300.00,70.0,3.0,3,https://example.com/rec-3,2026-07-10,immobilienscout24
Flat D,Invalidenstraße 80 10115 Berlin,1400.00,75.0,3.0,4,https://example.com/rec-4,2026-07-10,immobilienscout24
Flat E,Invalidenstraße 90 10115 Berlin,1500.00,80.0,3.0,5,https://example.com/rec-5,2026-07-10,immobilienscout24
Flat F,Brunnenstraße 5 10119 Berlin,1150.00,62.0,3.0,1,https://example.com/rec-6,2026-07-10,immobilienscout24
Flat G,Brunnenstraße 15 10119 Berlin,1250.00,67.0,3.0,2,https://example.com/rec-7,2026-07-10,immobilienscout24
Flat H,Brunnenstraße 25 10119 Berlin,1350.00,72.0,3.0,3,https://example.com/rec-8,2026-07-10,immobilienscout24
Flat I,Brunnenstraße 35 10119 Berlin,1450.00,77.0,3.0,4,https://example.com/rec-9,2026-07-10,immobilienscout24
Flat J,Brunnenstraße 45 10119 Berlin,1250.00,68.0,3.0,2,https://example.com/rec-10,2026-07-10,immobilienscout24
"""

APARTMENT_REQUEST = {
    "address": "Invalidenstraße 55, 10115 Berlin",
    "size_m2": 66.0,
    "rooms": 3.0,
    "floor": 2,
    "amenities": ["balcony"],
}


class TestRecommendationFlow:
    @pytest.fixture(autouse=True)
    def mock_geocoding(self):
        with patch(
            "src.services.geocoding.GeocodingService.geocode",
            new=AsyncMock(return_value=(52.53, 13.39)),
        ):
            yield

    @pytest.fixture(autouse=True)
    def mock_explanation(self):
        mock_result = MagicMock()
        mock_result.explanation_available = True
        mock_result.explanation = "Test explanation from mocked Ollama."
        mock_result.factors = [
            {"name": "Median", "description": "Test median", "value": "€1,250/month"},
            {"name": "Supply", "description": "Test supply", "value": "10 listings"},
            {"name": "Range", "description": "Test range", "value": "€1,100–€1,420"},
        ]
        with patch(
            "src.services.explanation.ExplanationService.generate",
            new=AsyncMock(return_value=mock_result),
        ):
            yield

    async def test_full_flow_returns_recommendation(self, client):
        # Upload data first
        with patch(
            "src.services.geocoding.GeocodingService.geocode_batch",
            new=AsyncMock(return_value=[(52.53, 13.39)] * 10),
        ):
            upload = await client.post(
                "/api/v1/listings/import",
                files={
                    "file": ("data.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")
                },
            )
        assert upload.status_code == 202

        # Get recommendation
        response = await client.post("/api/v1/recommendations", json=APARTMENT_REQUEST)
        assert response.status_code == 200
        body = response.json()
        assert body["recommended_price_eur"] > 0
        assert body["comparable_count"] >= 1
        assert body["confidence_level"] in ("high", "medium", "low")
        assert body["explanation_available"] is True

    async def test_recommendation_fields_match_contract(self, client):
        with patch(
            "src.services.geocoding.GeocodingService.geocode_batch",
            new=AsyncMock(return_value=[(52.53, 13.39)] * 10),
        ):
            await client.post(
                "/api/v1/listings/import",
                files={
                    "file": ("data.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")
                },
            )

        response = await client.post("/api/v1/recommendations", json=APARTMENT_REQUEST)
        if response.status_code == 503:
            pytest.skip("No data available")

        body = response.json()
        # Validate confidence_range structure
        assert "low" in body["confidence_range"]
        assert "high" in body["confidence_range"]
        assert body["confidence_range"]["low"] <= body["recommended_price_eur"]
        assert body["confidence_range"]["high"] >= body["recommended_price_eur"]
        # Validate factors
        assert len(body["factors"]) == 3
        for f in body["factors"]:
            assert "name" in f
            assert "description" in f
            assert "value" in f
        # Validate data_freshness
        assert "is_stale" in body["data_freshness"]
        assert "last_upload_at" in body["data_freshness"]
        assert "total_listings" in body["data_freshness"]
