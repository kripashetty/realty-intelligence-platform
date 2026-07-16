import csv as csv_module
import io
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation

REQUIRED_COLUMNS = {"address", "price", "size", "rooms", "url", "date", "provider"}


class InvalidRowError(Exception):
    pass


def normalize_german_decimal(value: str) -> Decimal:
    value = value.strip()
    # "1.250,00" → "1250.00"
    if re.match(r"^\d{1,3}(\.\d{3})+(,\d+)?$", value):
        value = value.replace(".", "").replace(",", ".")
    else:
        value = value.replace(",", ".")
    try:
        return Decimal(value)
    except InvalidOperation:
        raise ValueError(f"Cannot parse decimal: {value!r}")


def parse_listing_date(value: str) -> date:
    value = value.strip()
    parsed: date | None = None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            parsed = datetime.strptime(value, fmt).date()
            break
        except ValueError:
            continue
    if parsed is None:
        raise ValueError(f"Cannot parse date: {value!r}")
    today = datetime.now(UTC).date()
    if parsed > today:
        raise ValueError(f"Date {parsed} is in the future")
    if parsed < today - timedelta(days=365):
        raise ValueError(f"Date {parsed} is older than 365 days")
    return parsed


def validate_row(row: dict, row_number: int) -> dict:
    for col in ("address", "price", "size", "rooms", "url", "date", "provider"):
        if not row.get(col, "").strip():
            raise InvalidRowError(f"Missing required field: {col}")

    try:
        price = normalize_german_decimal(row["price"])
    except ValueError as exc:
        raise InvalidRowError(f"price: {exc}") from exc
    if price <= 0 or price >= 50000:
        raise InvalidRowError(f"price out of valid range: {price}")

    try:
        size = normalize_german_decimal(row["size"])
    except ValueError as exc:
        raise InvalidRowError(f"size: {exc}") from exc
    if size <= 5 or size >= 1000:
        raise InvalidRowError(f"size out of valid range: {size}")

    try:
        rooms = normalize_german_decimal(row["rooms"])
    except ValueError as exc:
        raise InvalidRowError(f"rooms: {exc}") from exc
    if rooms <= 0 or rooms > 20:
        raise InvalidRowError(f"rooms out of valid range: {rooms}")

    try:
        listing_date = parse_listing_date(row["date"])
    except ValueError as exc:
        raise InvalidRowError(f"date: {exc}") from exc

    floor_raw = row.get("floor", "").strip()
    floor: int | None = None
    if floor_raw:
        try:
            floor = int(floor_raw)
        except ValueError:
            raise InvalidRowError(f"floor must be an integer, got: {floor_raw!r}")

    title_raw = row.get("title", "").strip()
    title: str | None = title_raw if title_raw else None

    return {
        "title": title,
        "address": row["address"].strip(),
        "price_eur": price,
        "size_m2": size,
        "rooms": rooms,
        "floor": floor,
        "platform": row["provider"].strip(),
        "source_url": row["url"].strip(),
        "listing_date": listing_date,
    }


@dataclass
class ParseResult:
    valid_rows: list[dict] = field(default_factory=list)
    skip_reasons: list[dict] = field(default_factory=list)
    total_rows: int = 0


class CsvImportService:
    def parse(self, file: io.BytesIO) -> ParseResult:
        try:
            content = file.read().decode("utf-8-sig")
        except Exception as exc:
            raise ValueError(f"Cannot read file: {exc}") from exc

        reader = csv_module.DictReader(io.StringIO(content))

        if not reader.fieldnames:
            raise ValueError("CSV file is empty or has no header row")

        columns = {col.lower().strip() for col in reader.fieldnames}
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        result = ParseResult()
        seen: set[tuple[str, str]] = set()

        for i, raw_row in enumerate(reader, start=2):
            result.total_rows += 1

            # Extra fields land under None when commas appear inside unquoted values.
            if None in raw_row:
                result.skip_reasons.append(
                    {
                        "row_number": i,
                        "reason": (
                            "Row has too many fields"
                            " — unquoted comma inside a text value"
                        ),
                    }
                )
                continue

            row = {k.lower().strip(): (v or "") for k, v in raw_row.items()}

            try:
                validated = validate_row(row, row_number=i)
            except InvalidRowError as exc:
                result.skip_reasons.append({"row_number": i, "reason": str(exc)})
                continue

            dedup_key = (validated["source_url"], str(validated["listing_date"]))
            if dedup_key in seen:
                result.skip_reasons.append(
                    {
                        "row_number": i,
                        "reason": "Duplicate listing (url + date already exists)",
                    }
                )
                continue
            seen.add(dedup_key)
            result.valid_rows.append(validated)

        return result

    async def bulk_insert(
        self, db, batch_id: uuid.UUID, valid_rows: list[dict]
    ) -> None:


        from src.models.listing import Listing

        now = datetime.now(UTC)
        listings = [
            Listing(
                import_batch_id=batch_id,
                created_at=now,
                **row,
            )
            for row in valid_rows
        ]
        db.add_all(listings)
        await db.flush()
