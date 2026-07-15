"""T025 — Integration test for full CSV import flow.

Written before implementation (TDD red phase).
Tests: upload CSV → batch created → rows inserted → geocoding triggered.
Requires a live test database (conftest.py wires this up).
"""

import io
from unittest.mock import AsyncMock, patch

SAMPLE_CSV = """\
title,address,price,size,rooms,floor,url,date,provider
Nice flat,Invalidenstraße 50 10115 Berlin,1200.00,65.0,2.0,3,https://example.com/flow-1,2026-07-10,immobilienscout24
Cosy studio,Brunnenstraße 10 10119 Berlin,850.00,32.0,1.0,1,https://example.com/flow-2,2026-07-10,immowelt
Big apartment,Karl-Marx-Allee 1 10178 Berlin,2100.00,110.0,4.0,5,https://example.com/flow-3,2026-07-09,immobilienscout24
"""


class TestCsvImportFlow:
    @patch(
        "src.services.geocoding.GeocodingService.geocode_batch", new_callable=AsyncMock
    )
    async def test_upload_creates_batch_and_inserts_rows(
        self, mock_geocode, client, db_session
    ):
        mock_geocode.return_value = [(52.52, 13.40)] * 3

        response = await client.post(
            "/api/v1/listings/import",
            files={
                "file": ("listings.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")
            },
        )
        assert response.status_code == 202
        batch_id = response.json()["batch_id"]
        assert batch_id is not None

        # Poll status until not processing (or just check immediately in test)
        status_response = await client.get(f"/api/v1/listings/import/{batch_id}")
        assert status_response.status_code == 200
        body = status_response.json()
        assert body["total_rows"] == 3
        assert body["imported_rows"] == 3
        assert body["skipped_rows"] == 0

    @patch(
        "src.services.geocoding.GeocodingService.geocode_batch", new_callable=AsyncMock
    )
    async def test_duplicate_rows_are_counted_as_skipped(self, mock_geocode, client):
        mock_geocode.return_value = [(52.52, 13.40)]

        # Upload the same row twice in the same file
        csv_with_dup = (
            "title,address,price,size,rooms,floor,url,date,provider\n"
            "Flat A,Invalidenstr 1 Berlin,1100.00,50.0,2.0,2,https://example.com/dup-flow,2026-07-10,immobilienscout24\n"
            "Flat A,Invalidenstr 1 Berlin,1100.00,50.0,2.0,2,https://example.com/dup-flow,2026-07-10,immobilienscout24\n"
        )
        response = await client.post(
            "/api/v1/listings/import",
            files={"file": ("dup.csv", io.BytesIO(csv_with_dup.encode()), "text/csv")},
        )
        assert response.status_code == 202
        batch_id = response.json()["batch_id"]

        status = await client.get(f"/api/v1/listings/import/{batch_id}")
        body = status.json()
        assert body["imported_rows"] == 1
        assert body["skipped_rows"] == 1

    @patch(
        "src.services.geocoding.GeocodingService.geocode_batch", new_callable=AsyncMock
    )
    async def test_status_endpoint_reflects_imported_data(self, mock_geocode, client):
        mock_geocode.return_value = [(52.52, 13.40)] * 3

        await client.post(
            "/api/v1/listings/import",
            files={
                "file": ("listings.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")
            },
        )

        status = await client.get("/api/v1/listings/status")
        assert status.status_code == 200
        body = status.json()
        assert body["total_listings"] >= 3
        assert body["last_upload_at"] is not None
        assert body["latest_batch"] is not None
