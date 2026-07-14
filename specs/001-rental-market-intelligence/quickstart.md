# Quickstart Validation Guide: US1 — Get a Pricing Recommendation

**Purpose**: Validate that US1 works end-to-end after implementation.
**Prerequisites**: Backend running locally or on Azure; see project README for setup.

---

## Prerequisites

- Backend API running at `http://localhost:8000` (or your deployed URL)
- Frontend running at `http://localhost:5173`
- A Fredy CSV export file (or the sample file at `specs/001-rental-market-intelligence/fixtures/sample-listings.csv`)
- `curl` or any HTTP client (Postman, httpie, etc.)

---

## Step 1 — Verify Empty State

Before any data is uploaded, the platform should show a clear empty state.

```bash
curl http://localhost:8000/api/v1/listings/status
```

**Expected**:
```json
{ "total_listings": 0, "last_upload_at": null, "latest_batch": null }
```

In the browser: the recommendation form should display an empty-state prompt
instructing the operator to upload data.

---

## Step 2 — Upload a CSV

```bash
curl -X POST http://localhost:8000/api/v1/listings/import \
  -F "file=@specs/001-rental-market-intelligence/fixtures/sample-listings.csv"
```

**Expected** (202):
```json
{
  "batch_id": "<uuid>",
  "status": "processing"
}
```

Save the `batch_id` from the response.

---

## Step 3 — Poll Import Status

```bash
curl http://localhost:8000/api/v1/listings/import/<batch_id>
```

Poll until `status` is `completed`. Check that:
- `imported_rows` > 0
- Any `skipped_rows` have entries in `skip_reasons`
- `status` is `completed`, not `failed`

---

## Step 4 — Verify Data Freshness Indicator

```bash
curl http://localhost:8000/api/v1/listings/status
```

**Expected**:
```json
{
  "total_listings": <N>,
  "last_upload_at": "<timestamp>",
  "latest_batch": { ... }
}
```

In the browser: the data freshness indicator should update automatically (no page reload
required) and show the upload timestamp and listing count.

---

## Step 5 — Get a Pricing Recommendation (Happy Path)

```bash
curl -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "address": "Invalidenstraße 50, 10115 Berlin",
    "size_m2": 72.0,
    "rooms": 3.0,
    "floor": 2,
    "amenities": ["balcony"]
  }'
```

**Expected** (200):
- `recommended_price_eur` — a positive number in a realistic Berlin range (€600–€5,000)
- `confidence_range.low` < `recommended_price_eur` < `confidence_range.high`
- `comparable_count` ≥ 1
- `explanation` — non-empty string mentioning at least one concrete number from the data
- `factors` — array of exactly 3 objects, each with `name`, `description`, `value`
- `explanation_available: true`
- `data_freshness.is_stale: false`

---

## Step 6 — Validate Acceptance Scenarios

### Scenario 1: Standard recommendation

Use Step 5 above with a Berlin address. Verify all fields present and explanation
references the comparable count and price range.

### Scenario 2: Low-confidence (thin market)

Submit an address in an area with very few comparables (e.g., a niche Berlin suburb
not well-represented in the uploaded data):

```bash
curl -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "address": "Dorfstraße 1, 12529 Schönefeld",
    "size_m2": 60.0,
    "rooms": 2.0
  }'
```

**Expected**: `confidence_level` is `medium` or `low`; response still returns (not a 503).

### Scenario 3: Stale data warning

Manually set the `uploaded_at` of the latest batch to 3 days ago in the database,
then re-request a recommendation.

**Expected**: `data_freshness.is_stale: true` in the response; UI shows staleness warning.

### Scenario 4: No data state

Against a fresh database with no uploads, POST to `/api/v1/recommendations`.

**Expected**: 503 response with `error: "no_data"` and action guidance.

---

## Step 7 — CSV Validation Edge Cases

### Malformed rows

Upload a CSV that contains rows with missing required fields and invalid values:

**Expected**: 202 accepted; batch status shows `skipped_rows > 0` with `skip_reasons` listing
specific row numbers and reasons. Valid rows are still imported.

### Duplicate upload

Upload the same CSV twice.

**Expected**: Second import's `skip_reasons` show "Duplicate listing" for all rows.
`total_listings` count does not increase.

---

## Acceptance Criteria Reference

| Scenario | Verified by |
|----------|------------|
| Recommendation returned within 60 seconds | Time the POST /recommendations call |
| Explanation covers ≥ 3 factors | `factors` array length = 3 |
| Confidence range brackets recommended price | low < recommended < high |
| Data freshness updates without page reload | Observe UI after Step 4 |
| CSV of 1,000 rows processed in < 30 seconds | Time batch from upload to `completed` |
| Stale data flagged after 48 hours | Scenario 3 above |
