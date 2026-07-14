import math
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.listing import Listing

_BBOX_DEG = 0.018  # ~2km bounding box pre-filter
_DEFAULT_RADIUS_KM = 2.0
_SIZE_TOLERANCE = 0.20  # ±20%
_ROOMS_TOLERANCE = 1.0  # ±1 room


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class ComparablesService:
    async def _bounding_box_query(
        self, db: AsyncSession, lat: float, lng: float
    ) -> list[Listing]:
        result = await db.execute(
            select(Listing).where(
                and_(
                    Listing.latitude.isnot(None),
                    Listing.longitude.isnot(None),
                    Listing.latitude.between(lat - _BBOX_DEG, lat + _BBOX_DEG),
                    Listing.longitude.between(lng - _BBOX_DEG, lng + _BBOX_DEG),
                )
            )
        )
        return list(result.scalars().all())

    async def find_comparables(
        self,
        db: AsyncSession,
        lat: float,
        lng: float,
        size_m2: float,
        rooms: float,
        radius_km: float = _DEFAULT_RADIUS_KM,
    ) -> list[Listing]:
        candidates = await self._bounding_box_query(db, lat, lng)

        results = []
        for listing in candidates:
            if haversine_km(lat, lng, listing.latitude, listing.longitude) > radius_km:
                continue
            listing_size = float(listing.size_m2)
            if abs(listing_size - size_m2) / size_m2 > _SIZE_TOLERANCE:
                continue
            if abs(float(listing.rooms) - rooms) > _ROOMS_TOLERANCE:
                continue
            results.append(listing)

        return results

    async def find_comparables_no_geo(
        self,
        db: AsyncSession,
        size_m2: float,
        rooms: float,
    ) -> list[Listing]:
        """Fallback when apartment coordinates are unavailable: filter by size/rooms only."""
        result = await db.execute(
            select(Listing).where(
                and_(
                    Listing.size_m2.between(
                        size_m2 * (1 - _SIZE_TOLERANCE), size_m2 * (1 + _SIZE_TOLERANCE)
                    ),
                    Listing.rooms.between(rooms - _ROOMS_TOLERANCE, rooms + _ROOMS_TOLERANCE),
                )
            )
        )
        return list(result.scalars().all())
