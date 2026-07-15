"""T024 — Unit tests for geocoding service.

Written before implementation (TDD red phase).
src.services.geocoding does not exist yet.
Nominatim calls are mocked — no live API calls in tests.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.geocoding import GeocodingService


class TestGeocodingService:
    @pytest.fixture
    def service(self):
        return GeocodingService()

    @patch("src.services.geocoding.Nominatim")
    async def test_returns_lat_lng_for_valid_address(self, mock_nom_cls, service):
        mock_location = MagicMock()
        mock_location.latitude = 52.5200
        mock_location.longitude = 13.4050
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = mock_location
        mock_nom_cls.return_value = mock_geocoder

        lat, lng = await service.geocode("Invalidenstraße 50, 10115 Berlin")
        assert lat == pytest.approx(52.5200)
        assert lng == pytest.approx(13.4050)

    @patch("src.services.geocoding.Nominatim")
    async def test_returns_none_tuple_when_address_not_found(
        self, mock_nom_cls, service
    ):
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = None
        mock_nom_cls.return_value = mock_geocoder

        lat, lng = await service.geocode("Nonexistent Place, 99999 Nowhere")
        assert lat is None
        assert lng is None

    @patch("src.services.geocoding.Nominatim")
    async def test_returns_none_tuple_on_geocoding_exception(
        self, mock_nom_cls, service
    ):
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.side_effect = Exception("Network error")
        mock_nom_cls.return_value = mock_geocoder

        lat, lng = await service.geocode("Some Address, Berlin")
        assert lat is None
        assert lng is None

    async def test_geocode_batch_updates_all_listings(self, service):
        addresses = [
            "Invalidenstraße 50, 10115 Berlin",
            "Unter den Linden 1, 10117 Berlin",
        ]
        with patch.object(
            service, "geocode", new=AsyncMock(return_value=(52.52, 13.40))
        ):
            results = await service.geocode_batch(addresses)
        assert len(results) == 2
        assert all(r[0] == pytest.approx(52.52) for r in results)

    async def test_geocode_batch_handles_individual_failures_gracefully(self, service):
        async def side_effect(addr):
            if "Bad" in addr:
                return (None, None)
            return (52.52, 13.40)

        with patch.object(service, "geocode", new=AsyncMock(side_effect=side_effect)):
            results = await service.geocode_batch(
                ["Good Address Berlin", "Bad Address"]
            )
        assert results[0] == (pytest.approx(52.52), pytest.approx(13.40))
        assert results[1] == (None, None)
