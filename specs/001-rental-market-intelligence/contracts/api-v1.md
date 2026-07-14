# API Contract: Rental Market Intelligence — US1

**Base URL**: `/api/v1`
**Format**: JSON (application/json) unless noted
**Version**: v1
**Date**: 2026-07-13

All endpoints are defined here before UI implementation (Constitution Principle I: API-First).

---

## 1. Upload Listings CSV

Import rental listing data from a Fredy CSV export.

```
POST /api/v1/listings/import
Content-Type: multipart/form-data
```

**Request**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `file` | File | Yes | CSV file; max 50MB; UTF-8 or Latin-1 encoding |

**Response 202 — Accepted** (import started):

```json
{
  "batch_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "processing",
  "message": "Import started. Poll /api/v1/listings/import/{batch_id} for status."
}
```

**Response 400 — Bad Request** (not a CSV / empty file):

```json
{
  "error": "invalid_file",
  "message": "File must be a non-empty CSV."
}
```

**Response 422 — Unprocessable** (missing required columns):

```json
{
  "error": "invalid_schema",
  "message": "Missing required columns.",
  "missing_columns": ["url", "price"]
}
```

---

## 2. Get Import Batch Status

Poll the result of a CSV import.

```
GET /api/v1/listings/import/{batch_id}
```

**Path params**: `batch_id` — UUID returned from POST /listings/import

**Response 200 — OK**:

```json
{
  "batch_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "completed",
  "geocoding_status": "in_progress",
  "uploaded_at": "2026-07-13T10:30:00Z",
  "total_rows": 1024,
  "imported_rows": 1018,
  "skipped_rows": 6,
  "skip_reasons": [
    { "row_number": 14, "reason": "Missing required field: url" },
    { "row_number": 87, "reason": "price out of valid range: -50" },
    { "row_number": 203, "reason": "Duplicate listing (url + date already exists)" }
  ]
}
```

**status** values: `processing` | `completed` | `failed`
**geocoding_status** values: `pending` | `in_progress` | `completed`

**Response 404**:

```json
{ "error": "not_found", "message": "Batch not found." }
```

---

## 3. Get Dataset Status (Data Freshness)

Returns current dataset state for the data freshness indicator (FR-009).

```
GET /api/v1/listings/status
```

**Response 200 — data available**:

```json
{
  "total_listings": 4821,
  "last_upload_at": "2026-07-13T10:30:00Z",
  "latest_batch": {
    "batch_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "imported_rows": 1018,
    "uploaded_at": "2026-07-13T10:30:00Z",
    "geocoding_status": "completed"
  }
}
```

**Response 200 — no data yet**:

```json
{
  "total_listings": 0,
  "last_upload_at": null,
  "latest_batch": null
}
```

---

## 4. Get Pricing Recommendation

Core US1 endpoint. Accepts landlord's apartment details, returns a recommended listing price
with explanation.

```
POST /api/v1/recommendations
Content-Type: application/json
```

**Request body**:

```json
{
  "address": "Invalidenstraße 50, 10115 Berlin",
  "size_m2": 72.0,
  "rooms": 3.0,
  "floor": 2,
  "amenities": ["balcony", "elevator"]
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `address` | string | Yes | Non-empty; Berlin address |
| `size_m2` | float | Yes | 5–1000 |
| `rooms` | float | Yes | 0.5–20, increments of 0.5 |
| `floor` | integer | No | 0–50 |
| `amenities` | string[] | No | Values: `balcony`, `parking`, `elevator`, `furnished`, `garden`, `cellar` |

**Response 200 — OK**:

```json
{
  "recommendation_id": "a1b2c3d4-...",
  "recommended_price_eur": 1250.00,
  "confidence_range": {
    "low": 1100.00,
    "high": 1420.00
  },
  "confidence_level": "high",
  "comparable_count": 23,
  "percentile_rank": 58.3,
  "explanation": "Based on 23 comparable apartments in Mitte within 2km of your property, the median asking price is €1,250/month. Supply in this area is moderate (23 active listings), with prices ranging from €1,100 to €1,420. Your apartment's size (72m², 3 rooms) places it in the mid-market segment. Seasonal demand in July typically supports stable pricing. Listing at €1,250 positions you at the 58th percentile — competitively priced without underselling.",
  "factors": [
    {
      "name": "Comparable Market Median",
      "description": "23 comparable apartments within 2km have a median price of €1,250/month",
      "value": "€1,250/month"
    },
    {
      "name": "Local Supply Level",
      "description": "23 active comparable listings indicates moderate supply in your area",
      "value": "23 active listings"
    },
    {
      "name": "Price Distribution",
      "description": "Middle 50% of comparable prices range from €1,100 to €1,420",
      "value": "€1,100–€1,420 IQR"
    }
  ],
  "explanation_available": true,
  "data_freshness": {
    "last_upload_at": "2026-07-13T10:30:00Z",
    "total_listings": 4821,
    "is_stale": false
  },
  "generated_at": "2026-07-13T11:05:22Z"
}
```

**confidence_level** logic:
- `high`: comparable_count ≥ 10
- `medium`: comparable_count 5–9
- `low`: comparable_count 1–4

**is_stale**: `true` when `last_upload_at` is older than 48 hours.

**explanation_available**: `false` when Claude API is unavailable. All other fields still
populate normally.

**Response 503 — No Data**:

```json
{
  "error": "no_data",
  "message": "No listing data available. Please upload a CSV first.",
  "action": "Upload a Fredy CSV export at POST /api/v1/listings/import"
}
```

**Response 422 — Validation Error** (FastAPI standard):

```json
{
  "detail": [
    {
      "loc": ["body", "size_m2"],
      "msg": "value is not a valid float",
      "type": "type_error.float"
    }
  ]
}
```

---

## CSV Import Schema Reference

The `/api/v1/listings/import` endpoint expects a CSV with these columns.
Column order is flexible; header row is required.

| Column name | Required | Format | Example |
|-------------|----------|--------|---------|
| `title` | No | string | "Schöne 3-Zimmer-Wohnung in Mitte" |
| `address` | Yes | string | "Invalidenstraße 50, 10115 Berlin" |
| `price` | Yes | float or "1.250,00" | 1250.00 |
| `size` | Yes | float or "72,5" | 72.5 |
| `rooms` | Yes | float or "2,5" | 3.0 |
| `floor` | No | integer | 2 |
| `url` | Yes | URL string | "https://www.immobilienscout24.de/expose/123" |
| `date` | Yes | YYYY-MM-DD or DD.MM.YYYY | "2026-07-10" |
| `provider` | Yes | string | "immobilienscout24" |
