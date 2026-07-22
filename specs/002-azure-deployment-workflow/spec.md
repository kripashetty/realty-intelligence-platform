# Feature Specification: Azure Deployment Workflow

**Feature Branch**: `002-azure-deployment-workflow`

**Created**: 2026-07-16

**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Zero-touch Deployment on Merge to Main (Priority: P1)

A developer merges a pull request to `main`. Without any manual intervention, the application (backend and/or frontend) is built, tested, and deployed to the production environment on Azure within a predictable timeframe.

**Why this priority**: Manual deployment steps are a reliability risk and a bottleneck. Fully automated promotion from merge to production is the single highest-value DevOps improvement.

**Independent Test**: Merge a trivial change to `main` and verify the updated application is live on Azure within 10 minutes, with no human action after the merge.

**Acceptance Scenarios**:

1. **Given** a PR is merged to `main`, **When** the CI/CD pipeline runs, **Then** the backend container image is built, pushed to the registry, and the production container service is updated — all without manual intervention.
2. **Given** only frontend files changed, **When** the pipeline runs, **Then** only the frontend deployment job executes; backend deployment is skipped.
3. **Given** the backend deployment fails, **When** the pipeline detects the failure, **Then** the previous working version remains live and the team receives a failure notification.
4. **Given** a deployment succeeds, **When** a developer checks the pipeline, **Then** the deployed image tag and commit SHA are visible in the pipeline summary.

---

### User Story 2 — Infrastructure Provisioned Reproducibly via Code (Priority: P2)

A developer (or CI system) runs the infrastructure pipeline against a clean Azure subscription and all required resources are created automatically from code — no Azure Portal clicks required.

**Why this priority**: Without IaC, environment drift is inevitable. Reproducible infrastructure is a prerequisite for reliable staging and disaster recovery.

**Independent Test**: Destroy all Azure resources and re-run the infrastructure pipeline. The application should be fully operational within 30 minutes.

**Acceptance Scenarios**:

1. **Given** an empty Azure resource group, **When** the infrastructure pipeline runs, **Then** all required resources (container runtime, database, secret store, container registry) are provisioned and healthy.
2. **Given** infrastructure already exists, **When** the pipeline runs again, **Then** it applies only the delta without destroying live resources.
3. **Given** an invalid infrastructure configuration is pushed, **When** the pipeline validates it, **Then** it fails with a clear error before attempting to apply changes.

---

### User Story 3 — Database Migrations Applied Safely Before Traffic Shift (Priority: P2)

When a new backend version includes schema changes, the migration runs against the production database before the new container version begins serving traffic. Rollback is possible if migration fails.

**Why this priority**: Running migrations after traffic is live risks serving traffic against an incompatible schema, causing data corruption or outages.

**Independent Test**: Deploy a migration-bearing release and confirm the schema change is present in the database before any traffic reaches the new backend container.

**Acceptance Scenarios**:

1. **Given** a release contains pending migrations, **When** deployment runs, **Then** migrations execute and succeed before the new container revision receives traffic.
2. **Given** a migration fails, **When** the pipeline detects the failure, **Then** deployment halts, the existing container revision continues serving traffic, and the failure is reported.
3. **Given** no pending migrations, **When** deployment runs, **Then** the migration step is a no-op and does not delay deployment.

---

### User Story 4 — Secure Credential-free Pipeline Authentication (Priority: P3)

The CI/CD pipeline authenticates to Azure without storing any long-lived credentials or secrets in GitHub. If a credential is compromised, it cannot be replayed outside the pipeline context.

**Why this priority**: Long-lived service principal JSON secrets in GitHub Secrets are a common attack surface. Federated identity eliminates the credential entirely.

**Independent Test**: Remove all Azure credential secrets from the GitHub repository; verify the pipeline can still authenticate and deploy successfully.

**Acceptance Scenarios**:

1. **Given** the pipeline runs on a `push` to `main`, **When** it authenticates to Azure, **Then** it uses a short-lived token obtained via workload identity federation — no static secret is exchanged.
2. **Given** an unauthorized workflow file attempts to request an Azure token, **When** the federation policy evaluates the claim, **Then** authentication is denied.

---

### Edge Cases

- What happens when the Azure Container Registry is unreachable during a push?
- What happens if the production database is unavailable when a migration runs?
- What happens if two PRs are merged to `main` within seconds of each other — do both deployments complete safely without overwriting each other's image tag?
- What happens when the pipeline runs on a branch other than `main` — is deployment skipped?
- What if only infrastructure files changed but no application code changed?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CI/CD system MUST automatically build and deploy the backend on every merge to `main` that changes backend files.
- **FR-002**: The CI/CD system MUST automatically build and deploy the frontend on every merge to `main` that changes frontend files.
- **FR-003**: The pipeline MUST authenticate to Azure using short-lived federated credentials — no long-lived client secrets stored in version control or CI secrets.
- **FR-004**: All Azure infrastructure MUST be defined and provisioned via Infrastructure as Code; no resource may be created or modified via the Azure Portal.
- **FR-005**: Database schema migrations MUST run and succeed before the new application version begins serving production traffic.
- **FR-006**: A failed migration MUST halt the deployment and leave the current running version undisturbed.
- **FR-007**: Each successful deployment MUST record the deployed commit SHA and image tag in the pipeline output for traceability.
- **FR-008**: The infrastructure pipeline MUST be idempotent — running it twice against the same environment produces the same result without data loss.
- **FR-009**: Deployment jobs MUST be skipped automatically when no relevant files have changed (path-based triggers).
- **FR-010**: Application secrets (database password, API keys) MUST be stored in a managed secret store and injected at runtime — never in environment files committed to source control.
- **FR-011**: The CI/CD system MUST provide a clear failure notification (pipeline status, error log) when any deployment step fails.

### Key Entities

- **Deployment Pipeline**: The automated workflow triggered by a code merge; encompasses build, push, migrate, and deploy stages.
- **Infrastructure Stack**: The complete set of cloud resources required to run the application (compute, database, registry, secret store, networking).
- **Container Image**: An immutable, versioned artifact produced by the build stage and used by the deploy stage.
- **Database Migration**: A versioned, ordered script that advances the database schema to match the current application version.
- **Federated Identity Credential**: A trust relationship between the CI system and the cloud provider that issues short-lived tokens without requiring stored secrets.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A successful merge to `main` results in the updated application being live on Azure within 10 minutes, with no manual intervention required.
- **SC-002**: A complete infrastructure teardown and reprovision completes in under 30 minutes from a clean resource group.
- **SC-003**: Zero long-lived Azure credentials are stored in GitHub Secrets after the migration to federated identity is complete.
- **SC-004**: 100% of production deployments run database migrations before shifting traffic, verified by pipeline logs.
- **SC-005**: A failed deployment (build, migration, or container update) leaves the previous version serving traffic — zero unplanned downtime caused by a failed deploy.
- **SC-006**: All infrastructure resources are reproducible from IaC — no "snowflake" resources exist that cannot be recreated by running the infrastructure pipeline.

## Assumptions

- The project already has a working GitHub Actions CI setup for testing; this feature extends it with deployment stages.
- Azure Container Apps is the target compute platform for the backend, as specified in the constitution.
- Azure Static Web Apps hosts the frontend.
- Azure Database for PostgreSQL Flexible Server is the production database.
- Azure Container Registry stores backend container images.
- Azure Key Vault stores all application secrets at runtime.
- Bicep is the IaC language, per the constitution's Technology Standards.
- The GitHub repository has a single production environment (`main` branch → production); staging environments are out of scope for the initial implementation but the design should not preclude adding them later.
- The team has Owner or Contributor access to an Azure subscription to configure federated identity and assign roles.
