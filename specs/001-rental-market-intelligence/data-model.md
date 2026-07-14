# Data Model: Rental Market Intelligence — US1

**Feature**: `specs/001-rental-market-intelligence/`
**Date**: 2026-07-13
**Storage**: Azure PostgreSQL Flexible Server 15+
**ORM**: SQLAlchemy 2.x (async)

---

## Entities

### `import_batches`

Tracks each CSV upload event. Created immediately when a CSV is received.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, default gen_random_uuid() | |
| `uploaded_at` | TIMESTAMPTZ | NOT NULL, default now() | When the CSV was received |
| `total_rows` | INTEGER | NOT NULL | Rows in the CSV including header |
| `imported_rows` | INTEGER | NOT NULL, default 0 | Valid rows inserted |
| `skipped_rows` | INTEGER | NOT NULL, default 0 | Rows rejected |
| `skip_reasons` | JSONB | nullable | Array of `{row_number, reason}` objects |
| `status` | VARCHAR(20) | NOT NULL, default 'processing' | `processing`, `completed`, `failed` |
| `geocoding_status` | VARCHAR(20) | NOT NULL, default 'pending' | `pending`, `in_progress`, `completed` |

**Indexes**: `uploaded_at DESC` (for freshness queries)

---

### `listings`

One row per unique rental listing. Populated by CSV import.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, default gen_random_uuid() | |
| `import_batch_id` | UUID | FK → import_batches.id, NOT NULL | Which upload created this row |
| `title` | TEXT | nullable | Listing headline |
| `address` | TEXT | NOT NULL | Full address string |
| `latitude` | FLOAT | nullable | Geocoded; NULL until background task completes |
| `longitude` | FLOAT | nullable | Geocoded; NULL until background task completes |
| `price_eur` | NUMERIC(10,2) | NOT NULL | EUR/month, warm rent |
| `size_m2` | NUMERIC(7,2) | NOT NULL | Square metres |
| `rooms` | NUMERIC(4,1) | NOT NULL | Supports half-rooms (e.g., 2.5) |
| `floor` | SMALLINT | nullable | Ground floor = 0 |
| `platform` | VARCHAR(100) | NOT NULL | e.g., "immobilienscout24" |
| `source_url` | TEXT | NOT NULL | Original listing URL |
| `listing_date` | DATE | NOT NULL | Date published on source platform |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() | |

**Unique constraint**: `(source_url, listing_date)` — deduplication key

**Indexes**:
- `(latitude, longitude)` — bounding box pre-filter for comparable search
- `price_eur` — for percentile queries
- `(size_m2, rooms)` — for comparable filtering
- `listing_date DESC` — for recency filtering
- `import_batch_id` — for batch-level queries

---

### `pricing_recommendations`

Stores each recommendation generated for auditing and debugging. US1 treats this as an
append-only audit log; no user identity is stored (no auth in MVP).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, default gen_random_uuid() | |
| `generated_at` | TIMESTAMPTZ | NOT NULL, default now() | |
| `import_batch_id` | UUID | FK → import_batches.id, NOT NULL | Data snapshot used |
| `apt_address` | TEXT | NOT NULL | Landlord's apartment address |
| `apt_latitude` | FLOAT | nullable | Geocoded at request time |
| `apt_longitude` | FLOAT | nullable | |
| `apt_size_m2` | NUMERIC(7,2) | NOT NULL | |
| `apt_rooms` | NUMERIC(4,1) | NOT NULL | |
| `apt_floor` | SMALLINT | nullable | |
| `apt_amenities` | JSONB | nullable | Array of strings e.g. `["balcony","parking"]` |
| `comparable_count` | INTEGER | NOT NULL | Number of listings used |
| `recommended_price_eur` | NUMERIC(10,2) | NOT NULL | Median of comparables |
| `confidence_low_eur` | NUMERIC(10,2) | NOT NULL | 25th percentile |
| `confidence_high_eur` | NUMERIC(10,2) | NOT NULL | 75th percentile |
| `percentile_rank` | FLOAT | NOT NULL | 0–100; where recommended price sits in comparables |
| `explanation` | TEXT | nullable | Claude-generated text; NULL if API unavailable |
| `factors` | JSONB | NOT NULL | Array of `{name, description, value}` |
| `comparable_listing_ids` | JSONB | NOT NULL | Array of listing UUIDs used |
| `confidence_level` | VARCHAR(10) | NOT NULL | `high` (≥10), `medium` (5–9), `low` (<5) |

**Indexes**: `generated_at DESC`

---

## Entity Relationships

```
import_batches (1) ──< listings (many)
import_batches (1) ──< pricing_recommendations (many)
```

`pricing_recommendations` records which `import_batch` was the active dataset at generation
time, enabling future auditing of "what data produced this recommendation."

---

## Validation Rules (enforced at service layer)

| Entity | Field | Rule |
|--------|-------|------|
| listings | price_eur | MUST be > 0 and < 50,000 (sanity bound) |
| listings | size_m2 | MUST be > 5 and < 1,000 |
| listings | rooms | MUST be > 0 and ≤ 20 |
| listings | listing_date | MUST NOT be in the future; MUST be within last 365 days |
| listings | source_url | MUST be a valid URL |
| pricing_recommendations | comparable_count | MUST be ≥ 1 (0 = no data, return 503) |

---

## State Transitions

### `import_batches.status`

```
[CSV received] → processing → completed
                           ↘ failed  (unrecoverable parse error)
```

### `import_batches.geocoding_status`

```
[batch created] → pending → in_progress → completed
```

Geocoding runs as a background task after the batch reaches `completed`. Listings are
usable for non-proximity comparables (price/size/rooms filter) before geocoding completes.
