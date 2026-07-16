import asyncio
import logging

from geopy.exc import GeocoderServiceError
from geopy.geocoders import Nominatim

logger = logging.getLogger(__name__)

_RATE_LIMIT_DELAY = 1.0  # Nominatim: max 1 req/sec

# Germany bounding box — reject geocoding results outside this range
_DE_LAT_MIN, _DE_LAT_MAX = 47.2, 55.1
_DE_LNG_MIN, _DE_LNG_MAX = 5.8, 15.1


class GeocodingService:
    def __init__(self, user_agent: str = "realty-intelligence-platform/1.0"):
        self._user_agent = user_agent

    async def geocode(self, address: str) -> tuple[float | None, float | None]:
        geocoder = Nominatim(user_agent=self._user_agent)
        try:
            location = await asyncio.get_event_loop().run_in_executor(
                None, lambda: geocoder.geocode(address, timeout=10)
            )
            if location is None:
                return (None, None)
            lat, lng = location.latitude, location.longitude
            if not (
                _DE_LAT_MIN <= lat <= _DE_LAT_MAX and _DE_LNG_MIN <= lng <= _DE_LNG_MAX
            ):
                logger.warning(
                    "Geocoding %r returned non-Germany coords (%.4f, %.4f) — ignoring",
                    address,
                    lat,
                    lng,
                )
                return (None, None)
            return (lat, lng)
        except (GeocoderServiceError, Exception) as exc:
            logger.warning("Geocoding failed for %r: %s", address, exc)
            return (None, None)

    async def geocode_batch(
        self, addresses: list[str]
    ) -> list[tuple[float | None, float | None]]:
        results = []
        for address in addresses:
            lat_lng = await self.geocode(address)
            results.append(lat_lng)
            await asyncio.sleep(_RATE_LIMIT_DELAY)
        return results

    async def update_listing_coordinates(self, db, batch_id) -> None:

        from sqlalchemy import select, update

        from src.models.import_batch import GeocodingStatus, ImportBatch
        from src.models.listing import Listing

        # Mark in_progress
        await db.execute(
            update(ImportBatch)
            .where(ImportBatch.id == batch_id)
            .values(geocoding_status=GeocodingStatus.in_progress)
        )
        await db.commit()

        result = await db.execute(
            select(Listing.id, Listing.address).where(
                Listing.import_batch_id == batch_id
            )
        )
        rows = result.fetchall()

        for listing_id, address in rows:
            lat, lng = await self.geocode(address)
            await db.execute(
                update(Listing)
                .where(Listing.id == listing_id)
                .values(latitude=lat, longitude=lng)
            )
            await db.commit()
            await asyncio.sleep(_RATE_LIMIT_DELAY)

        await db.execute(
            update(ImportBatch)
            .where(ImportBatch.id == batch_id)
            .values(geocoding_status=GeocodingStatus.completed)
        )
        await db.commit()
