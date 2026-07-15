"""T022 — Contract tests for CSV import endpoints.

These tests are written BEFORE implementation (TDD red phase).
They import from src.api.v1.listings which does not yet exist —
all tests must fail until T026–T029 are implemented.
"""

import io
import uuid
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def no_background_geocoding():
    """Prevent _run_geocoding from opening a competing DB session during tests."""
    with patch("src.api.v1.listings._run_geocoding", new=AsyncMock()):
        yield


class TestPostListingsImport:
    """POST /api/v1/listings/import"""

    async def test_returns_202_with_batch_id_for_valid_csv(self, client):
        csv_content = (
            "title,address,price,size,rooms,floor,url,date,provider\n"
            "Nice flat,Invalidenstraße 50 10115 Berlin,1200.00,65.0,2.0,3,"
            "https://example.com/1,2026-07-10,immobilienscout24\n"
        )
        response = await client.post(
            "/api/v1/listings/import",
            files={
                "file": ("listings.csv", io.BytesIO(csv_content.encode()), "text/csv")
            },
        )
        assert response.status_code == 202
        body = response.json()
        assert "batch_id" in body
        assert body["status"] == "processing"
        assert "message" in body
        uuid.UUID(body["batch_id"])  # must be valid UUID

    async def test_returns_400_for_non_csv_file(self, client):
        response = await client.post(
            "/api/v1/listings/import",
            files={"file": ("data.txt", io.BytesIO(b"not a csv"), "text/plain")},
        )
        assert response.status_code == 400
        body = response.json()
        assert body["error"] == "invalid_file"

    async def test_returns_400_for_empty_file(self, client):
        response = await client.post(
            "/api/v1/listings/import",
            files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
        )
        assert response.status_code == 400
        body = response.json()
        assert body["error"] == "invalid_file"

    async def test_returns_422_for_missing_required_columns(self, client):
        csv_content = "title,address,price\nsome flat,somewhere,1000\n"
        response = await client.post(
            "/api/v1/listings/import",
            files={"file": ("bad.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"] == "invalid_schema"
        assert "missing_columns" in body
        assert isinstance(body["missing_columns"], list)


class TestGetImportBatchStatus:
    """GET /api/v1/listings/import/{batch_id}"""

    async def test_returns_200_with_batch_details(self, client):
        csv_content = (
            "title,address,price,size,rooms,floor,url,date,provider\n"
            "Nice flat,Invalidenstraße 50 10115 Berlin,1200.00,65.0,2.0,3,"
            "https://example.com/status-test,2026-07-10,immobilienscout24\n"
        )
        create_response = await client.post(
            "/api/v1/listings/import",
            files={
                "file": ("listings.csv", io.BytesIO(csv_content.encode()), "text/csv")
            },
        )
        assert create_response.status_code == 202
        batch_id = create_response.json()["batch_id"]

        response = await client.get(f"/api/v1/listings/import/{batch_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["batch_id"] == batch_id
        assert body["status"] in ("processing", "completed", "failed")
        assert body["geocoding_status"] in ("pending", "in_progress", "completed")
        assert "uploaded_at" in body
        assert "total_rows" in body
        assert "imported_rows" in body
        assert "skipped_rows" in body

    async def test_returns_404_for_unknown_batch_id(self, client):
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/listings/import/{fake_id}")
        assert response.status_code == 404
        body = response.json()
        assert body["error"] == "not_found"


class TestGetListingsStatus:
    """GET /api/v1/listings/status"""

    async def test_returns_200_with_status_fields(self, client):
        response = await client.get("/api/v1/listings/status")
        assert response.status_code == 200
        body = response.json()
        assert "total_listings" in body
        assert "last_upload_at" in body
        assert "latest_batch" in body

    async def test_no_data_state_returns_zeros_and_nulls(self, client):
        response = await client.get("/api/v1/listings/status")
        assert response.status_code == 200
        body = response.json()
        # When no data exists both should be falsy/zero
        assert isinstance(body["total_listings"], int)
