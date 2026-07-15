<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 1.0.1 (PATCH — technology standards clarification)

Modified: Technology Standards table — AI/LLM row
  - 1.0.0: Claude API (Anthropic) | claude-sonnet-5 or latest
  - 1.0.1: Ollama (self-hosted) | llama3.1:8b or mistral:7b-instruct; CPU for MVP, GPU-ready

Rationale: Switching to Ollama keeps all data on-premises, eliminates per-token API costs,
and removes the external API dependency. GPU inference deferred to post-MVP.
CPU-only inference comfortably fits the 60-second recommendation SLA.

Affected artifacts:
  - specs/001-rental-market-intelligence/research.md ✅ Decision 3 updated
  - specs/001-rental-market-intelligence/plan.md     ✅ Dependencies + structure updated

Templates reviewed:
  - .specify/templates/plan-template.md   ✅ No update needed
  - .specify/templates/spec-template.md   ✅ No update needed
  - .specify/templates/tasks-template.md  ✅ No update needed

Deferred TODOs: GPU workload profile (Azure Container Apps) — revisit post-MVP.
-->

# Realty Intelligence Platform Constitution

## Core Principles

### I. API-First Design

The FastAPI backend MUST define the authoritative contract for all data and operations.
The React TypeScript frontend MUST consume data exclusively via versioned OpenAPI endpoints.

- Every backend capability MUST be exposed via a documented endpoint before any UI is built
  against it
- OpenAPI schema is auto-generated from FastAPI route definitions and serves as the
  single source of truth for the frontend-backend contract
- Direct database access from the frontend is prohibited
- Breaking API changes MUST increment the API major version (`/v1/`, `/v2/`)

**Rationale**: Contract-first development prevents frontend/backend drift, enables parallel
development, and ensures the API is always independently testable.

### II. Test-First (NON-NEGOTIABLE)

TDD is mandatory. Tests MUST be written and confirmed failing before any implementation code
is written. The Red-Green-Refactor cycle is strictly enforced.

- No implementation code is committed without a prior failing test
- Backend: pytest with test coverage enforced on all service and route layers
- Frontend: Vitest + React Testing Library; component tests before component implementation
- Contract tests MUST be written before endpoint implementation
- Integration tests MUST cover all user-story acceptance scenarios

**Rationale**: TDD enforces clarity of intent, catches regressions early, and produces
inherently testable designs. Skipping it is not a time-saver — it is technical debt that
compounds.

### III. Data-Grounded AI Insights

All AI-generated market analysis MUST be grounded in real, verifiable property data.

- AI insights MUST clearly indicate they are AI-generated in all UI surfaces
- Every insight MUST cite the underlying data source (MLS records, transaction history,
  census data, etc.)
- Hallucinated or unverifiable claims MUST NOT be surfaced to users
- AI responses MUST be validated against a schema before being stored or displayed
- Model outputs that cannot be grounded in source data MUST fall back to a
  "data unavailable" state rather than presenting an estimate

**Rationale**: Realty decisions involve large financial commitments. Users MUST be able
to trust and verify insights; ungrounded AI output in this domain creates legal and
reputational risk.

### IV. Layered Architecture (Strict Separation)

The system is divided into three strict tiers. Cross-tier coupling is prohibited.

- **Data tier**: Azure Database for PostgreSQL — accessed only by the service layer
- **Service tier**: Python FastAPI — business logic, AI orchestration, data access
- **Presentation tier**: React TypeScript — UI only; contains no business logic

Rules:
- Business logic MUST NOT live in React components; it belongs in FastAPI services
- React components MUST NOT import from service-layer modules
- Database queries MUST NOT be inlined in route handlers; service/repository classes
  encapsulate data access
- Each tier MUST be independently deployable and testable

**Rationale**: Strict layering keeps concerns isolated, enables independent scaling,
and prevents the "big ball of mud" that plagues full-stack features built under time
pressure.

### V. Azure-Native Deployment

All infrastructure MUST be provisioned on Microsoft Azure. Workloads MUST be containerized.
Infrastructure as Code (IaC) is mandatory for every environment.

- Backend: Dockerized FastAPI deployed to Azure Container Apps
- Frontend: Built React app served from Azure Static Web Apps
- Database: Azure Database for PostgreSQL Flexible Server
- Secrets: Azure Key Vault — no secrets in source code or environment files committed
  to version control
- IaC: Bicep or Terraform; all infrastructure changes MUST go through IaC, never
  via the Azure Portal directly
- CI/CD: GitHub Actions pipelines for all environments (dev, staging, prod)

**Rationale**: Azure was selected as the target platform. Codifying it here prevents
infrastructure sprawl and ensures every environment is reproducible.

## Technology Standards

These are the fixed technology choices for the Realty Intelligence Platform. Deviations
require a constitution amendment.

| Layer | Technology | Version Constraint |
|-------|-----------|-------------------|
| Frontend framework | React | 18+ |
| Frontend language | TypeScript | strict mode enabled |
| Backend framework | Python FastAPI | 0.110+ |
| Backend language | Python | 3.11+ |
| Database | Azure PostgreSQL Flexible Server | 15+ |
| ORM | SQLAlchemy | 2.x (async) |
| AI / LLM | Ollama (self-hosted) | llama3.1:8b or mistral:7b-instruct; CPU for MVP, GPU-ready post-MVP |
| Container runtime | Docker | — |
| Hosting (backend) | Azure Container Apps | — |
| Hosting (frontend) | Azure Static Web Apps | — |
| IaC | Bicep | — |
| CI/CD | GitHub Actions | — |
| Backend testing | pytest + httpx | — |
| Frontend testing | Vitest + React Testing Library | — |

**TypeScript strict mode** means: `strict: true` in `tsconfig.json`. No `any` without
an explicit justification comment.

## Development Workflow

### Branching

- `main` is the production branch; direct pushes are prohibited
- Feature branches follow the naming convention: `###-short-feature-name`
  (e.g., `001-property-search`, `002-market-insights`)
- Branch numbers are sequential and correspond to the feature spec number in `/specs/`

### Pull Requests

- All PRs MUST target `main` as the base branch
- Every PR MUST include passing tests (all red-green cycles complete)
- Every PR MUST pass the Constitution Check from the feature's `plan.md`
- PRs require at least one reviewer approval before merge
- Merge strategy: squash merge to keep `main` history linear
- Closed issues MUST be listed one per line using `Closes #N` — never comma-separated

### Quality Gates (mandatory before merge)

1. All tests pass (`pytest` backend, `vitest` frontend)
2. `uv run ruff check src/ tests/` exits 0 — zero lint errors
3. TypeScript compilation with zero errors
4. No `any` types without justification comment
5. OpenAPI schema unchanged OR version bumped if contract changed
6. IaC validated (`bicep build` or `terraform validate`) if infrastructure changed
7. No secrets or credentials in diff

### Python Coding Standards

These apply to all Python code in `backend/src/` and `backend/tests/`. They match the
`ruff` config (`line-length = 88`, `target-version = py311`, `select = E W F I N UP`).

**Run before every commit**: `uv run ruff check src/ tests/`

Rules most commonly violated in generated or fast-typed code — know these before writing:

| Rule | Requirement | Common mistake |
|------|-------------|----------------|
| E501 | Max 88 chars per line | Long string literals, log messages, docstrings |
| UP042 | Use `enum.StrEnum` not `(str, enum.Enum)` | Python <3.11 habit |
| N806 | Function-scoped variables must be lowercase | Math constants like `R = 6371` |
| E741 | No ambiguous names: `l`, `O`, `I` | List comprehension variable `l` |

When a string literal is the only thing exceeding the limit, split it with implicit
concatenation across lines rather than adding a `# noqa` suppression.

## Governance

This constitution supersedes all other practices, conventions, or verbal agreements.
When a conflict arises between a feature spec and this constitution, the constitution wins
unless an amendment is ratified.

**Amendment procedure**:
1. Open a PR modifying this file with the proposed change
2. State the motivation, impact on existing features, and migration plan (if any)
3. PR requires approval from the project lead before merge
4. Update `LAST_AMENDED_DATE` and increment `CONSTITUTION_VERSION` per the versioning policy

**Versioning policy**:
- MAJOR: Removal or redefinition of a core principle
- MINOR: New principle or section added; materially expanded guidance
- PATCH: Clarifications, wording fixes, non-semantic refinements

**Compliance**: All PRs and design reviews MUST verify compliance with this constitution.
Complexity beyond what the principles allow MUST be justified in the feature's
`plan.md` Complexity Tracking table.

**Version**: 1.0.2 | **Ratified**: 2026-07-13 | **Last Amended**: 2026-07-15
