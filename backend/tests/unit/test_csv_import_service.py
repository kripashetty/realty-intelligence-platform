"""T023 — Unit tests for CSV import service.

Written before implementation (TDD red phase).
src.services.csv_import does not exist yet.
"""
import io
from decimal import Decimal

import pandas as pd
import pytest

from src.services.csv_import import (
    CsvImportService,
    InvalidRowError,
    normalize_german_decimal,
    parse_listing_date,
    validate_row,
)

REQUIRED_COLUMNS = {"title", "address", "price", "size", "rooms", "url", "date", "provider"}


class TestNormalizeGermanDecimal:
    def test_passes_through_plain_float_string(self):
        assert normalize_german_decimal("1250.00") == Decimal("1250.00")

    def test_converts_german_format_with_dot_thousands(self):
        assert normalize_german_decimal("1.250,00") == Decimal("1250.00")

    def test_converts_german_decimal_comma(self):
        assert normalize_german_decimal("72,5") == Decimal("72.5")

    def test_strips_whitespace(self):
        assert normalize_german_decimal("  1200.00  ") == Decimal("1200.00")

    def test_raises_on_unparseable_value(self):
        with pytest.raises(ValueError):
            normalize_german_decimal("not-a-number")


class TestParseListingDate:
    def test_parses_iso_format(self):
        from datetime import date
        assert parse_listing_date("2026-07-10") == date(2026, 7, 10)

    def test_parses_german_dot_format(self):
        from datetime import date
        assert parse_listing_date("10.07.2026") == date(2026, 7, 10)

    def test_raises_on_future_date(self):
        with pytest.raises(ValueError, match="future"):
            parse_listing_date("2099-01-01")

    def test_raises_on_date_older_than_365_days(self):
        with pytest.raises(ValueError, match="365"):
            parse_listing_date("2000-01-01")

    def test_raises_on_invalid_format(self):
        with pytest.raises(ValueError):
            parse_listing_date("not-a-date")


class TestValidateRow:
    def _base_row(self):
        return {
            "title": "Nice flat",
            "address": "Invalidenstraße 50, 10115 Berlin",
            "price": "1200.00",
            "size": "65.0",
            "rooms": "2.0",
            "floor": "3",
            "url": "https://example.com/1",
            "date": "2026-07-10",
            "provider": "immobilienscout24",
        }

    def test_valid_row_returns_normalized_dict(self):
        result = validate_row(self._base_row(), row_number=1)
        assert result["price_eur"] == Decimal("1200.00")
        assert result["size_m2"] == Decimal("65.0")
        assert result["rooms"] == Decimal("2.0")
        assert result["platform"] == "immobilienscout24"
        assert result["source_url"] == "https://example.com/1"

    def test_missing_required_field_raises(self):
        row = self._base_row()
        del row["address"]
        with pytest.raises(InvalidRowError, match="address"):
            validate_row(row, row_number=2)

    def test_price_below_zero_raises(self):
        row = self._base_row()
        row["price"] = "-50"
        with pytest.raises(InvalidRowError, match="price"):
            validate_row(row, row_number=3)

    def test_price_above_50000_raises(self):
        row = self._base_row()
        row["price"] = "99999"
        with pytest.raises(InvalidRowError, match="price"):
            validate_row(row, row_number=4)

    def test_size_below_5_raises(self):
        row = self._base_row()
        row["size"] = "3"
        with pytest.raises(InvalidRowError, match="size"):
            validate_row(row, row_number=5)

    def test_rooms_above_20_raises(self):
        row = self._base_row()
        row["rooms"] = "25"
        with pytest.raises(InvalidRowError, match="rooms"):
            validate_row(row, row_number=6)

    def test_german_decimal_price_is_normalized(self):
        row = self._base_row()
        row["price"] = "1.250,00"
        result = validate_row(row, row_number=7)
        assert result["price_eur"] == Decimal("1250.00")

    def test_german_decimal_size_is_normalized(self):
        row = self._base_row()
        row["size"] = "72,5"
        result = validate_row(row, row_number=8)
        assert result["size_m2"] == Decimal("72.5")

    def test_floor_is_optional(self):
        row = self._base_row()
        row["floor"] = ""
        result = validate_row(row, row_number=9)
        assert result["floor"] is None

    def test_title_is_optional(self):
        row = self._base_row()
        row["title"] = ""
        result = validate_row(row, row_number=10)
        assert result["title"] is None


class TestCsvImportServiceParse:
    def _make_csv(self, rows: list[str]) -> io.BytesIO:
        header = "title,address,price,size,rooms,floor,url,date,provider\n"
        content = header + "\n".join(rows) + "\n"
        return io.BytesIO(content.encode())

    def test_parse_raises_on_missing_required_column(self):
        csv = io.BytesIO(b"title,address,price\nsome flat,somewhere,1000\n")
        service = CsvImportService()
        with pytest.raises(ValueError, match="Missing required columns"):
            service.parse(csv)

    def test_parse_returns_valid_rows_and_skip_reasons(self):
        csv = self._make_csv([
            "Nice flat,Invalidenstraße 50 10115 Berlin,1200.00,65.0,2.0,3,https://example.com/a,2026-07-10,immobilienscout24",
            ",Bad row,-50,3,0,,not-a-url,2026-07-10,immobilienscout24",
        ])
        service = CsvImportService()
        result = service.parse(csv)
        assert len(result.valid_rows) == 1
        assert len(result.skip_reasons) == 1
        assert result.skip_reasons[0]["row_number"] == 2

    def test_deduplication_marks_second_occurrence_as_skipped(self):
        duplicate_url = "https://example.com/dup"
        row = f"Flat,Invalidenstraße 50 10115 Berlin,1200,65,2,3,{duplicate_url},2026-07-10,immobilienscout24"
        csv = self._make_csv([row, row])
        service = CsvImportService()
        result = service.parse(csv)
        assert len(result.valid_rows) == 1
        assert len(result.skip_reasons) == 1
        assert "Duplicate" in result.skip_reasons[0]["reason"]

    def test_german_decimal_rows_are_parsed_correctly(self):
        csv = self._make_csv([
            "Flat,Invalidenstraße 50 10115 Berlin,1.250,00,72,5,2,5,3,https://example.com/g,2026-07-10,immobilienscout24",
        ])
        service = CsvImportService()
        result = service.parse(csv)
        assert len(result.valid_rows) == 1
