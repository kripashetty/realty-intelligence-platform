# Research: Rental Market Intelligence — US1

**Feature**: `specs/001-rental-market-intelligence/`
**Date**: 2026-07-13
**Scope**: US1 — Get a Pricing Recommendation (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-009)

---

## Decision 1: Address Geocoding (for proximity-based comparable filtering)

**Decision**: Nominatim (OpenStreetMap) via the `geopy` Python library.

**Rationale**: Geocoding converts a Berlin apartment address into lat/lng coordinates, enabling
Haversine-distance filtering of comparables. Nominatim is free, requires no API key, has good
coverage of Berlin addresses, and is sufficient for the batch-import rate (1 req/sec limit is
acceptable when geocoding happens during CSV processing, not on the recommendation hot path).

**Alternatives considered**:
- Google Maps Geocoding API — accurate but costs money per request; overkill for MVP
- HERE Geocoding API — free tier available but adds an external account dependency

**Implementation note**: Geocode each listing address at import time and store `latitude`,
`longitude` on the listing row. If geocoding fails, store NULLs and exclude that listing from
proximity-based comparables (it can still appear in non-proximity filters).

---

## Decision 2: Statistical Method for Pricing Recommendation

**Decision**: Median of comparable listing prices as the recommended price. 25th–75th percentile
range as the confidence interval. `scipy.stats.percentileofscore` for competitive percentile rank.

**Rationale**: Median is robust to outliers (luxury or misclassified listings), which are common
in scraped real estate data. The IQR (25th–75th) gives a defensible confidence range without
overfitting to the specific dataset. The percentile rank of the recommended price satisfies FR-007
(competitive positioning).

**Alternatives considered**:
- Mean price — sensitive to outliers; a single luxury listing skews the result significantly
- Linear regression on size/rooms/location — overfits on small comparable sets (<20 listings);
  adds complexity without meaningful accuracy gain at MVP scale
- Automated Valuation Model (AVM) — appropriate post-MVP when historical data is available

**Libraries**: Python `statistics` (median), `numpy` (percentile), `scipy.stats` (percentile rank).
All are standard data science dependencies with no licensing constraints.

---

## Decision 3: Natural Language Explanation via Ollama (Self-Hosted)

**Decision**: Ollama running as a sidecar container alongside FastAPI in Azure Container Apps.
Model: `llama3.1:8b` (primary) or `mistral:7b-instruct` (fallback). FastAPI calls Ollama via
its local HTTP API at `http://ollama:11434`. CPU-only inference for MVP; architecture is
GPU-ready for post-MVP upgrade by swapping to a dedicated workload profile.

**Rationale**: Self-hosting eliminates per-token API costs, removes the external network
dependency, and keeps all listing data within the Azure subscription boundary. CPU inference
on Azure Container Apps takes ~10–20 seconds for a 200-word explanation — comfortably within
the 60-second SC-001 SLA. When GPU is added post-MVP, inference drops to ~1–3 seconds with
no application code changes (just infrastructure).

**Prompt strategy** (identical structure to a cloud LLM):
- System prompt: instructs the model to act as a Berlin rental market analyst, cite only the
  provided data, produce exactly 3 named factors, respond in plain English under 200 words
- User message: structured JSON of `{ apartment, comparables_stats, market_context }`
- Response schema validation: must contain `explanation` string and `factors` array of 3 objects
  with `name` and `description` keys; reject and fall back if schema invalid

**Graceful degradation**: If Ollama is unreachable or inference times out (>45s), the
recommendation endpoint still returns the full statistical output (price, confidence range,
comparables count) with `explanation_available: false` — the feature never hard-fails.

**GPU upgrade path**: Add a dedicated workload profile with an NVIDIA T4 SKU to the Container
Apps Environment via Bicep. No application code changes required.

**Alternatives considered**:
- Claude API — higher quality output but per-token cost, external data dependency, and requires
  API key management; ruled out in favour of self-hosted for MVP cost and privacy reasons
- GPT-4 / Gemini — same concerns as Claude API; also not in constitution
- Rule-based template strings — deterministic but rigid; poor readability for varied inputs

---

## Decision 4: Fredy CSV Export Schema

**Decision**: Define a canonical import schema aligned to Fredy's SQLite listing fields. The
platform accepts CSV with the following columns (order-insensitive, header row required):

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `title` | string | No | Listing headline |
| `address` | string | Yes | Full street address, Berlin |
| `price` | float | Yes | EUR/month, warm rent (Warmmiete) |
| `size` | float | Yes | m² |
| `rooms` | float | Yes | e.g., 2.5 |
| `floor` | integer | No | Ground = 0 |
| `url` | string | Yes | Source listing URL (used for deduplication) |
| `date` | date | Yes | ISO 8601: YYYY-MM-DD |
| `provider` | string | Yes | e.g., "immobilienscout24", "immowelt" |

**Normalization rules applied at import**:
- `price`: strip currency symbols, commas; convert to float
- `size`: strip "m²" suffix; convert to float
- `rooms`: accept "2,5" (German decimal) and "2.5"; normalize to float
- `date`: accept DD.MM.YYYY (German format) and YYYY-MM-DD
- `url`: strip trailing slashes and query parameters for deduplication key

**Rationale**: This schema maps directly to Fredy's SQLite `listings` table columns. Defining it
explicitly allows other data sources (manual CSV, other scrapers) to feed the platform without
changing the import logic.

---

## Decision 5: Geospatial Proximity for Comparable Filtering

**Decision**: Store `latitude` and `longitude` as `FLOAT` columns on the `listings` table.
Compute Haversine distance in the Python service layer to filter comparables within a configurable
radius (default: 2km).

**Rationale**: At MVP scale (1,000–10,000 listings in Berlin), Python-side Haversine computation
over pre-filtered results (by approximate bounding box in SQL) is fast enough (<100ms). This avoids
the PostGIS extension dependency on Azure PostgreSQL, which requires explicit enablement and adds
operational complexity.

**Bounding box pre-filter**: Before Haversine, SQL filters listings within ±0.018° lat/lng (~2km),
reducing the Python computation to a small subset.

**Alternatives considered**:
- PostGIS `ST_DWithin` — best long-term solution but requires extension activation on Azure
  PostgreSQL Flexible Server and schema migration; recommended post-MVP
- Cube/earthdistance PostgreSQL extensions — lighter than PostGIS but less portable

---

## Decision 6: CSV Processing Strategy

**Decision**: Synchronous processing for MVP (files expected ≤10k rows). Parse with `pandas`,
validate row-by-row, collect errors, bulk-insert valid rows via SQLAlchemy.

**Rationale**: Async background tasks (Celery, FastAPI BackgroundTasks) add deployment complexity.
At 1,000 rows with geocoding (1 req/sec Nominatim limit), processing takes ~20 minutes — too slow
for synchronous. Solution: geocode asynchronously after bulk insert using a FastAPI background
task. Import returns immediately with batch_id; geocoding runs in background. Comparables that
lack coordinates are excluded from proximity filter but included in non-geo fallback.

**Import flow**:
1. Parse CSV → validate schema → collect invalid rows
2. Bulk insert valid rows (without coordinates) → return batch_id immediately
3. Background task: geocode each new listing address → update lat/lng

**Alternatives considered**:
- Celery + Redis — correct for production scale; deferred to post-MVP
- Synchronous geocoding during import — blocks request for minutes; rejected

---

## Decision 7: Frontend Data Fetching

**Decision**: TanStack Query (React Query v5) for all server state in the React frontend.

**Rationale**: React Query handles loading/error states, request deduplication, background
refetching, and cache invalidation — all needed for the CSV upload status polling (batch_id
status check) and the data freshness indicator. No global state manager (Redux, Zustand) is
needed for US1's simple, stateless forms.

**Alternatives considered**:
- Plain `fetch` + `useState` — sufficient for simple calls but lacks polling and cache
  invalidation needed for upload status
- Redux Toolkit Query — heavier setup than React Query for this scope
