---
description: "Task list for Rental Market Intelligence — US1: Get a Pricing Recommendation"
---

# Tasks: Rental Market Intelligence — US1

**Input**: Design documents from `specs/001-rental-market-intelligence/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/api-v1.md ✅

**Tests**: Included — TDD is NON-NEGOTIABLE per Constitution Principle II. Tests MUST be written
and confirmed failing before any implementation task begins. Red → Green → Refactor cycle enforced.

**Scope**: US1 only (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-009)

## Phase Overview

| Phase | Goal | Tasks | Status |
|-------|------|-------|--------|
| **Phase 1: Setup** | Project structure, tooling, Dockerfiles, fixture CSV | T001–T010 (10 tasks) | ✅ Complete |
| **Phase 2: Foundational** | DB models, migrations, FastAPI skeleton, Bicep infra | T011–T021 (11 tasks) | ⬜ Not started |
| **Phase 3: US1 — CSV Import** | CSV upload endpoint + validation + background geocoding (FR-001, FR-002) | T022–T029 (8 tasks) | ⬜ Not started |
| **Phase 3: US1 — Recommendation** | Comparable filter + statistical pricing + Ollama explanation (FR-003–FR-006, FR-009) | T030–T039 (10 tasks) | ⬜ Not started |
| **Phase 3: US1 — Frontend** | React components: form, uploader, result, freshness bar | T040–T049 (10 tasks) | ⬜ Not started |
| **Phase 4: Polish & CI/CD** | GitHub Actions pipelines, end-to-end validation, README | T050–T053 (4 tasks) | ⬜ Not started |

**Total**: 53 tasks across 6 phases · Implement one phase at a time · Create GitHub issues per phase before starting it

---

### Phase 1 — Setup (T001–T010)
Project skeleton, tooling config, Dockerfiles, local docker-compose with Ollama, and the sample CSV fixture used in all validation scenarios.

### Phase 2 — Foundational (T011–T021)
SQLAlchemy engine + session, Alembic migrations for all 3 tables, FastAPI app entry point, and all Bicep IaC modules (PostgreSQL, Key Vault, Container Apps with Ollama sidecar). Nothing in Phase 3 can start until this is complete.

### Phase 3 — US1: CSV Import (T022–T029)
TDD block: write failing tests first (contract + unit + integration), then implement the CSV import service (parse, validate, normalise, deduplicate), the Nominatim geocoding background task, and the listings API router (3 endpoints).

### Phase 3 — US1: Recommendation (T030–T039)
TDD block: write failing tests first, then implement the comparables service (bounding-box SQL + Haversine), pricing service (median, IQR, percentile rank), explanation service (Ollama via httpx, prompt, fallback), and the recommendations API router.

### Phase 3 — US1: Frontend (T040–T049)
TDD block: write failing Vitest component tests first, then implement the typed API service layer and four components (ApartmentForm, CsvUploader, RecommendationResult, DataFreshnessBar), assembled into RecommendationPage.

### Phase 4 — Polish & CI/CD (T050–T053)
GitHub Actions workflows for backend (pytest → Docker build) and frontend (vitest → Static Web Apps deploy), full quickstart.md end-to-end validation run, and project README.

---

## Format: `[ID] [P?] [Story?] Description — file path`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[US1]**: Maps to User Story 1 from spec.md

---

## Phase 1: Setup

**Purpose**: Initialise project structure and tooling for both backend and frontend.

- [X] T001 Create project directory structure: `backend/`, `frontend/`, `infra/`, `.github/workflows/`
- [X] T002 [P] Initialise Python backend project with FastAPI, SQLAlchemy, pytest dependencies in `backend/pyproject.toml`
- [X] T003 [P] Initialise React TypeScript frontend project with Vite in `frontend/`
- [X] T004 [P] Configure TypeScript strict mode (`strict: true`) in `frontend/tsconfig.json`
- [X] T005 [P] Configure backend linting and formatting (ruff, black) in `backend/pyproject.toml`
- [X] T006 [P] Configure frontend linting and formatting (ESLint, Prettier) in `frontend/package.json`
- [X] T007 [P] Create backend `Dockerfile` (Python 3.11 slim, non-root user) in `backend/Dockerfile`
- [X] T008 [P] Create frontend `Dockerfile` (Node build + nginx serve) in `frontend/Dockerfile`
- [X] T009 Create `docker-compose.yml` for local development (FastAPI + PostgreSQL + Ollama with `llama3.1:8b`) at `docker-compose.yml`
- [X] T010 [P] Create sample CSV fixture with 50 Berlin listings in `specs/001-rental-market-intelligence/fixtures/sample-listings.csv` (matches schema in `contracts/api-v1.md`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database models, migrations, FastAPI skeleton, and infrastructure that all US1
implementation depends on.

⚠️ **CRITICAL**: No US1 implementation can begin until this phase is complete.

- [ ] T011 Set up SQLAlchemy async engine, session factory, and base class in `backend/src/db.py`
- [ ] T012 Initialise Alembic for async SQLAlchemy migrations in `backend/alembic/`
- [ ] T013 Create FastAPI application entry point with `/api/v1` router registration in `backend/src/main.py`
- [ ] T014 [P] Create `ImportBatch` SQLAlchemy model (fields per `data-model.md`) in `backend/src/models/import_batch.py`
- [ ] T015 [P] Create `Listing` SQLAlchemy model with unique constraint `(source_url, listing_date)` and lat/lng indexes in `backend/src/models/listing.py`
- [ ] T016 [P] Create `PricingRecommendation` SQLAlchemy model in `backend/src/models/recommendation.py`
- [ ] T017 Create Alembic migration for `import_batches`, `listings`, `pricing_recommendations` tables in `backend/alembic/versions/001_initial_schema.py` (depends on T014, T015, T016)
- [ ] T018 [P] Create Bicep module for Azure PostgreSQL Flexible Server 15+ in `infra/modules/postgresql.bicep`
- [ ] T019 [P] Create Bicep module for Azure Key Vault in `infra/modules/keyvault.bicep`
- [ ] T020 Create Bicep module for Container Apps environment (FastAPI container + Ollama sidecar, CPU workload profile, GPU-ready parameter) in `infra/modules/container-apps.bicep`
- [ ] T021 Create Bicep main file and dev/prod parameter files in `infra/main.bicep`, `infra/parameters/dev.bicepparam`, `infra/parameters/prod.bicepparam`

**Checkpoint**: Foundation complete — US1 implementation can begin.

---

## Phase 3: User Story 1 — Get a Pricing Recommendation (Priority: P1) 🎯 MVP

**Goal**: A landlord submits apartment details and receives a recommended listing price with
a confidence range and a plain-language explanation citing 3 real market factors.

**Independent Test**: Upload `fixtures/sample-listings.csv`, submit a Berlin apartment form,
verify a recommendation with explanation is returned within 60 seconds.

---

### Backend — CSV Import Tests ⚠️ WRITE FIRST, CONFIRM FAILING

> Tests MUST fail before T027–T029 are implemented.

- [ ] T022 [US1] Write failing contract tests for `POST /api/v1/listings/import`, `GET /api/v1/listings/import/{batch_id}`, and `GET /api/v1/listings/status` (202, 400, 404, 422 responses) in `backend/tests/contract/test_listings_import.py`
- [ ] T023 [P] [US1] Write failing unit tests for CSV parsing, row validation, price/size normalization, German decimal handling, and deduplication logic in `backend/tests/unit/test_csv_import_service.py`
- [ ] T024 [P] [US1] Write failing unit tests for geocoding service (Nominatim address lookup, coordinate storage, NULL handling on failure) in `backend/tests/unit/test_geocoding_service.py`
- [ ] T025 [P] [US1] Write failing integration test for full CSV import flow: upload CSV → batch created → rows inserted → background geocoding triggered in `backend/tests/integration/test_csv_import_flow.py`

### Backend — CSV Import Implementation

- [ ] T026 [P] [US1] Create listing import/status Pydantic request and response schemas in `backend/src/schemas/listings.py`
- [ ] T027 [US1] Implement `csv_import` service: CSV parse (pandas), row validation, price/size/date normalization, deduplication, bulk insert via SQLAlchemy in `backend/src/services/csv_import.py` (depends on T026)
- [ ] T028 [US1] Implement `geocoding` background task service: Nominatim lookup via geopy, 1 req/sec rate limiting, update listing lat/lng, update `import_batch.geocoding_status` in `backend/src/services/geocoding.py` (depends on T027)
- [ ] T029 [US1] Implement listings API router: `POST /import` (accepts CSV, starts background geocoding), `GET /import/{batch_id}`, `GET /status` in `backend/src/api/v1/listings.py` (depends on T026, T027, T028)

**Checkpoint**: CSV upload flow complete and contract tests passing.

---

### Backend — Recommendation Tests ⚠️ WRITE FIRST, CONFIRM FAILING

> Tests MUST fail before T036–T039 are implemented.

- [ ] T030 [US1] Write failing contract tests for `POST /api/v1/recommendations` (200 with all fields, 422 validation errors, 503 no-data state) in `backend/tests/contract/test_recommendations.py`
- [ ] T031 [P] [US1] Write failing unit tests for comparables service: bounding-box SQL pre-filter, Haversine distance calculation, ±20% size filter, ±1 room filter in `backend/tests/unit/test_comparables_service.py`
- [ ] T032 [P] [US1] Write failing unit tests for pricing service: median calculation, 25th/75th percentile confidence range, percentile rank, `confidence_level` thresholds (high/medium/low) in `backend/tests/unit/test_pricing_service.py`
- [ ] T033 [P] [US1] Write failing unit tests for explanation service: Ollama HTTP call via httpx, prompt construction with real data, response schema validation, graceful fallback when Ollama unreachable in `backend/tests/unit/test_explanation_service.py`
- [ ] T034 [P] [US1] Write failing integration test for full recommendation flow: apartment input → comparable filter → statistical analysis → Ollama explanation → structured response in `backend/tests/integration/test_recommendation_flow.py`

### Backend — Recommendation Implementation

- [ ] T035 [P] [US1] Create recommendation request/response Pydantic schemas (including `factors`, `confidence_range`, `data_freshness`, `explanation_available` fields per `contracts/api-v1.md`) in `backend/src/schemas/recommendations.py`
- [ ] T036 [US1] Implement `comparables` service: bounding-box SQL pre-filter (±0.018° lat/lng), Python Haversine distance, size ±20%, rooms ±1 filters in `backend/src/services/comparables.py` (depends on T035)
- [ ] T037 [US1] Implement `pricing` service: median recommended price, 25th/75th percentile confidence range, `scipy.stats.percentileofscore` percentile rank, `confidence_level` classification in `backend/src/services/pricing.py` (depends on T036)
- [ ] T038 [US1] Implement `explanation` service: httpx async call to Ollama (`http://ollama:11434/api/generate`), structured prompt with real comparable stats, JSON schema validation of response, 45s timeout with graceful fallback in `backend/src/services/explanation.py` (depends on T037)
- [ ] T039 [US1] Implement recommendations API router: geocode apartment address, call comparables → pricing → explanation services, assemble and return full response, handle no-data 503 in `backend/src/api/v1/recommendations.py` (depends on T035, T036, T037, T038)

**Checkpoint**: Full backend recommendation flow complete and all backend tests passing.

---

### Frontend — Component Tests ⚠️ WRITE FIRST, CONFIRM FAILING

> Tests MUST fail before T044–T049 are implemented.

- [ ] T040 [P] [US1] Write failing component tests for `ApartmentForm`: renders all fields, validates required fields, calls onSubmit with correct payload in `frontend/tests/ApartmentForm.test.tsx`
- [ ] T041 [P] [US1] Write failing component tests for `CsvUploader`: file selection, upload triggers POST, polls batch status, displays import report (imported/skipped counts) in `frontend/tests/CsvUploader.test.tsx`
- [ ] T042 [P] [US1] Write failing component tests for `RecommendationResult`: renders price, confidence range, explanation text, 3 factors, percentile rank, and confidence level badge in `frontend/tests/RecommendationResult.test.tsx`
- [ ] T043 [P] [US1] Write failing component tests for `DataFreshnessBar`: shows last upload time, listing count, stale warning when `is_stale: true`, empty state prompt in `frontend/tests/DataFreshnessBar.test.tsx`

### Frontend — Implementation

- [ ] T044 [P] [US1] Create typed API service layer with wrappers for all 4 endpoints and TypeScript interfaces matching `contracts/api-v1.md` in `frontend/src/services/api.ts`
- [ ] T045 [P] [US1] Implement `DataFreshnessBar` component (last upload timestamp, listing count, stale warning, auto-refresh via TanStack Query) in `frontend/src/components/DataFreshnessBar.tsx` (depends on T044)
- [ ] T046 [P] [US1] Implement `CsvUploader` component (file input, POST to import endpoint, poll batch status every 2s until `completed`, display import report) in `frontend/src/components/CsvUploader.tsx` (depends on T044)
- [ ] T047 [P] [US1] Implement `ApartmentForm` component (address, size\_m2, rooms, floor, amenities checkboxes, React Hook Form validation) in `frontend/src/components/ApartmentForm.tsx` (depends on T044)
- [ ] T048 [US1] Implement `RecommendationResult` component (recommended price, confidence range, confidence level badge, explanation text, 3 factors list, percentile rank, stale data warning) in `frontend/src/components/RecommendationResult.tsx` (depends on T044)
- [ ] T049 [US1] Assemble `RecommendationPage` from all components with empty-state handling (no data uploaded yet) in `frontend/src/pages/RecommendationPage.tsx` (depends on T045, T046, T047, T048)

**Checkpoint**: US1 fully functional end-to-end. Run quickstart.md Steps 1–7 to validate.

---

## Phase 4: Polish & CI/CD

**Purpose**: CI pipelines, documentation, and end-to-end validation.

- [ ] T050 [P] Create GitHub Actions backend CI workflow (pytest + ruff on PR; Docker build + push to ACR on merge to main) in `.github/workflows/backend-ci.yml`
- [ ] T051 [P] Create GitHub Actions frontend CI workflow (vitest + tsc on PR; deploy to Azure Static Web Apps on merge to main) in `.github/workflows/frontend-ci.yml`
- [ ] T052 Run all 7 quickstart.md validation steps end-to-end against running stack; confirm all acceptance scenarios pass
- [ ] T053 [P] Write project setup README covering local dev with docker-compose, Fredy CSV export steps, and environment variable reference in `README.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately; most tasks parallel
- **Foundational (Phase 2)**: Depends on Phase 1 completion — blocks all US1 work
- **US1 (Phase 3)**: Depends on Phase 2 completion
  - CSV import tests (T022–T025): parallel with each other
  - CSV import implementation (T026–T029): sequential after tests
  - Recommendation tests (T030–T034): parallel with each other; can start alongside CSV implementation
  - Recommendation implementation (T036→T037→T038→T039): sequential chain
  - Frontend tests (T040–T043): parallel; can start alongside backend work
  - Frontend implementation (T044–T048): parallel; T049 depends on all
- **Polish (Phase 4)**: Depends on Phase 3 checkpoint validation

### Within US1 — Critical Chains

```
Backend CSV path:
T022 (tests) → T027 (service) → T028 (geocoding) → T029 (router)

Backend Recommendation path:
T030–T034 (tests) → T036 (comparables) → T037 (pricing) → T038 (explanation) → T039 (router)

Frontend path:
T040–T043 (tests) → T044 (api.ts) → T045/T046/T047 [parallel] → T048 → T049
```

### Parallel Opportunities

All Setup tasks marked [P] can run in parallel after T001.
All Foundational model tasks (T014, T015, T016) can run in parallel.
All backend test tasks within a group (T022–T025, T030–T034) are parallel.
All frontend test tasks (T040–T043) are parallel.
Frontend component implementations T045, T046, T047 are parallel.
CI workflows T050, T051 are parallel.

---

## Parallel Example: US1 Backend Tests

```bash
# Launch all CSV import test files in parallel:
Task: "Write failing contract tests for listings endpoints in backend/tests/contract/test_listings_import.py"
Task: "Write failing unit tests for CSV import service in backend/tests/unit/test_csv_import_service.py"
Task: "Write failing unit tests for geocoding service in backend/tests/unit/test_geocoding_service.py"
Task: "Write failing integration test for CSV import flow in backend/tests/integration/test_csv_import_flow.py"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Backend CSV import: write tests → confirm failing → implement → confirm passing
4. Backend recommendation: write tests → confirm failing → implement → confirm passing
5. Frontend: write tests → confirm failing → implement → confirm passing
6. **STOP AND VALIDATE**: Run quickstart.md Steps 1–7 in full
7. Phase 4: CI/CD and documentation

### TDD Checkpoints (mandatory per Constitution Principle II)

Before implementing any task group, verify:
- [ ] Tests are written in the correct test file
- [ ] `pytest` (backend) or `vitest` (frontend) shows tests **FAILING** (red)
- [ ] Only then begin implementation
- [ ] After implementation: tests pass (green)
- [ ] Refactor if needed; re-run to confirm still green

---

## Notes

- [P] tasks = different files, no incomplete dependencies — safe to parallelise
- [US1] label maps every task to User Story 1 for traceability
- Tests come before implementation in every section — this is enforced by the constitution
- Ollama must be running locally (via docker-compose) before any explanation service tests
- Nominatim geocoding tests should use a fixture/mock to avoid hitting the live API in CI
- Commit after each completed task group (tests passing green)
