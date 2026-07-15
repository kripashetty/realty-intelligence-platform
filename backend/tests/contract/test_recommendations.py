"""T030 — Contract tests for recommendations endpoint.

Written before implementation (TDD red phase).
src.api.v1.recommendations does not exist yet.
"""

import pytest

VALID_REQUEST = {
    "address": "Invalidenstraße 50, 10115 Berlin",
    "size_m2": 72.0,
    "rooms": 3.0,
    "floor": 2,
    "amenities": ["balcony", "elevator"],
}


class TestPostRecommendations:
    """POST /api/v1/recommendations"""

    async def test_returns_503_when_no_listing_data(self, client):
        response = await client.post("/api/v1/recommendations", json=VALID_REQUEST)
        # With no data loaded, must return 503
        assert response.status_code == 503
        body = response.json()
        assert body["error"] == "no_data"
        assert "action" in body

    async def test_returns_422_for_missing_address(self, client):
        payload = {**VALID_REQUEST}
        del payload["address"]
        response = await client.post("/api/v1/recommendations", json=payload)
        assert response.status_code == 422

    async def test_returns_422_for_size_below_minimum(self, client):
        payload = {**VALID_REQUEST, "size_m2": 3.0}
        response = await client.post("/api/v1/recommendations", json=payload)
        assert response.status_code == 422

    async def test_returns_422_for_size_above_maximum(self, client):
        payload = {**VALID_REQUEST, "size_m2": 1500.0}
        response = await client.post("/api/v1/recommendations", json=payload)
        assert response.status_code == 422

    async def test_returns_422_for_rooms_above_maximum(self, client):
        payload = {**VALID_REQUEST, "rooms": 25.0}
        response = await client.post("/api/v1/recommendations", json=payload)
        assert response.status_code == 422

    async def test_returns_422_for_invalid_amenity_value(self, client):
        payload = {**VALID_REQUEST, "amenities": ["balcony", "invalid_amenity"]}
        response = await client.post("/api/v1/recommendations", json=payload)
        assert response.status_code == 422

    async def test_floor_is_optional(self, client):
        payload = {k: v for k, v in VALID_REQUEST.items() if k != "floor"}
        # Should not return 422 for missing floor
        response = await client.post("/api/v1/recommendations", json=payload)
        assert response.status_code != 422

    async def test_amenities_is_optional(self, client):
        payload = {k: v for k, v in VALID_REQUEST.items() if k != "amenities"}
        response = await client.post("/api/v1/recommendations", json=payload)
        assert response.status_code != 422

    async def test_200_response_has_all_required_fields(self, client, db_session):
        """Requires listing data — use a populated fixture (skipped if no data)."""
        response = await client.post("/api/v1/recommendations", json=VALID_REQUEST)
        if response.status_code == 503:
            pytest.skip("No listing data available")
        assert response.status_code == 200
        body = response.json()
        assert "recommendation_id" in body
        assert "recommended_price_eur" in body
        assert "confidence_range" in body
        assert "low" in body["confidence_range"]
        assert "high" in body["confidence_range"]
        assert "confidence_level" in body
        assert body["confidence_level"] in ("high", "medium", "low")
        assert "comparable_count" in body
        assert "percentile_rank" in body
        assert "explanation" in body
        assert "factors" in body
        assert isinstance(body["factors"], list)
        assert len(body["factors"]) == 3
        assert "explanation_available" in body
        assert "data_freshness" in body
        assert "generated_at" in body
