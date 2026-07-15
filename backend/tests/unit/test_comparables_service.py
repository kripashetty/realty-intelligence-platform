"""T031 — Unit tests for comparables service.

Written before implementation (TDD red phase).
src.services.comparables does not exist yet.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.comparables import ComparablesService, haversine_km


class TestHaversineKm:
    def test_same_point_is_zero(self):
        assert haversine_km(52.52, 13.40, 52.52, 13.40) == pytest.approx(0.0)

    def test_known_berlin_distance(self):
        # Brandenburger Tor to Alexanderplatz ~3.2km
        km = haversine_km(52.5163, 13.3777, 52.5219, 13.4132)
        assert 2.5 < km < 4.0

    def test_symmetry(self):
        d1 = haversine_km(52.52, 13.40, 52.53, 13.41)
        d2 = haversine_km(52.53, 13.41, 52.52, 13.40)
        assert d1 == pytest.approx(d2)


class TestComparablesService:
    @pytest.fixture
    def service(self):
        return ComparablesService()

    def _make_listing(self, price, size, rooms, lat=52.52, lng=13.40):
        return MagicMock(
            price_eur=Decimal(str(price)),
            size_m2=Decimal(str(size)),
            rooms=Decimal(str(rooms)),
            latitude=lat,
            longitude=lng,
        )

    async def test_filters_by_haversine_radius(self, service):
        # Listing within 2km
        near = self._make_listing(1200, 65, 2, lat=52.525, lng=13.405)
        # Listing >2km away
        far = self._make_listing(1200, 65, 2, lat=52.56, lng=13.50)

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(
                service, "_bounding_box_query", AsyncMock(return_value=[near, far])
            )
            results = await service.find_comparables(
                db=mock_db,
                lat=52.52,
                lng=13.40,
                size_m2=65.0,
                rooms=2.0,
                radius_km=2.0,
            )
        assert near in results
        assert far not in results

    async def test_filters_by_size_within_20_percent(self, service):
        target_size = 65.0
        within = self._make_listing(1200, 70, 2)  # 70/65 ≈ 1.077 — within 20%
        outside = self._make_listing(1200, 100, 2)  # 100/65 ≈ 1.538 — outside 20%

        mock_db = AsyncMock()
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(
                service,
                "_bounding_box_query",
                AsyncMock(return_value=[within, outside]),
            )
            results = await service.find_comparables(
                db=mock_db,
                lat=52.52,
                lng=13.40,
                size_m2=target_size,
                rooms=2.0,
                radius_km=2.0,
            )
        assert within in results
        assert outside not in results

    async def test_filters_by_rooms_within_one(self, service):
        target_rooms = 3.0
        within = self._make_listing(1200, 65, 2.5)  # |2.5-3| = 0.5 ≤ 1
        outside = self._make_listing(1200, 65, 5.0)  # |5-3| = 2 > 1

        mock_db = AsyncMock()
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(
                service,
                "_bounding_box_query",
                AsyncMock(return_value=[within, outside]),
            )
            results = await service.find_comparables(
                db=mock_db,
                lat=52.52,
                lng=13.40,
                size_m2=65.0,
                rooms=target_rooms,
                radius_km=2.0,
            )
        assert within in results
        assert outside not in results

    async def test_returns_empty_list_when_no_comparables(self, service):
        mock_db = AsyncMock()
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(service, "_bounding_box_query", AsyncMock(return_value=[]))
            results = await service.find_comparables(
                db=mock_db,
                lat=52.52,
                lng=13.40,
                size_m2=65.0,
                rooms=2.0,
                radius_km=2.0,
            )
        assert results == []
