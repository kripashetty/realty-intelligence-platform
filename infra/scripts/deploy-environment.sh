#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPOSITORY_ROOT="$(cd "${INFRA_DIR}/.." && pwd)"

ENVIRONMENT="${1:-}"

case "$ENVIRONMENT" in
  dev | prod)
    ;;
  *)
    printf 'Usage: %s <dev|prod>\n' "$0" >&2
    exit 1
    ;;
esac

SHARED_OUTPUTS_FILE="${INFRA_DIR}/.outputs/shared.env"

[[ -f "$SHARED_OUTPUTS_FILE" ]] ||
  fail "Shared outputs file not found: $SHARED_OUTPUTS_FILE. Run deploy-shared.sh first."

# shellcheck source=/dev/null
source "$SHARED_OUTPUTS_FILE"

[[ -n "${ACR_NAME:-}" ]] ||
  fail "ACR_NAME was not found in $SHARED_OUTPUTS_FILE."

[[ -n "${ACR_LOGIN_SERVER:-}" ]] ||
  fail "ACR_LOGIN_SERVER was not found in $SHARED_OUTPUTS_FILE."

ENVIRONMENT_TEMPLATE="${INFRA_DIR}/environment/main.bicep"
ENVIRONMENT_PARAMETERS="${INFRA_DIR}/environment/parameters/${ENVIRONMENT}.bicepparam"

SHARED_RESOURCE_GROUP="${SHARED_RESOURCE_GROUP:-realty-shared-rg}"
SHARED_DEPLOYMENT_NAME="${SHARED_DEPLOYMENT_NAME:-realty-shared}"

ENVIRONMENT_RESOURCE_GROUP="${ENVIRONMENT_RESOURCE_GROUP:-realty-${ENVIRONMENT}-rg}"
AZURE_LOCATION="${AZURE_LOCATION:-northeurope}"
AZURE_SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:-}"

BACKEND_IMAGE_REPOSITORY="${BACKEND_IMAGE_REPOSITORY:-realty-backend}"
BACKEND_BUILD_CONTEXT="${BACKEND_BUILD_CONTEXT:-${REPOSITORY_ROOT}/backend}"
BACKEND_DOCKERFILE="${BACKEND_DOCKERFILE:-${BACKEND_BUILD_CONTEXT}/Dockerfile}"

DEPLOYMENT_NAME="${ENVIRONMENT_DEPLOYMENT_NAME:-realty-${ENVIRONMENT}}"

RUN_JOBS="${RUN_JOBS:-true}"
SKIP_IMAGE_BUILD="${SKIP_IMAGE_BUILD:-false}"

log() {
  printf '\n[%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"
}

fail() {
  printf '\nERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 ||
    fail "Required command '$1' is not installed."
}

require_file() {
  [[ -f "$1" ]] || fail "Required file not found: $1"
}

wait_for_job_execution() {
  local job_name="$1"
  local execution_name="$2"
  local timeout_seconds="${JOB_WAIT_TIMEOUT_SECONDS:-7500}"
  local poll_seconds="${JOB_POLL_SECONDS:-10}"
  local elapsed=0
  local status=""

  while (( elapsed < timeout_seconds )); do
    status="$(
      az containerapp job execution show \
        --name "$job_name" \
        --resource-group "$ENVIRONMENT_RESOURCE_GROUP" \
        --job-execution-name "$execution_name" \
        --query properties.status \
        --output tsv 2>/dev/null || true
    )"

    printf '[%s] %s: %s\n' \
      "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
      "$execution_name" \
      "${status:-Pending}"

    case "$status" in
      Succeeded)
        return 0
        ;;

      Failed)
        printf '\nJob execution failed.\n' >&2

        az containerapp job execution show \
          --name "$job_name" \
          --resource-group "$ENVIRONMENT_RESOURCE_GROUP" \
          --job-execution-name "$execution_name" \
          --output jsonc >&2 || true

        return 1
        ;;
    esac

    sleep "$poll_seconds"
    elapsed=$((elapsed + poll_seconds))
  done

  printf 'Timed out waiting for execution %s.\n' "$execution_name" >&2
  return 1
}

require_command az
require_command git

require_file "$ENVIRONMENT_TEMPLATE"
require_file "$ENVIRONMENT_PARAMETERS"

if [[ "$SKIP_IMAGE_BUILD" != "true" ]]; then
  require_command docker
  require_file "$BACKEND_DOCKERFILE"
fi

log "Checking Azure authentication"

az account show >/dev/null 2>&1 ||
  fail "Not signed in to Azure. Run: az login"

if [[ -n "$AZURE_SUBSCRIPTION_ID" ]]; then
  log "Selecting Azure subscription: $AZURE_SUBSCRIPTION_ID"
  az account set --subscription "$AZURE_SUBSCRIPTION_ID"
fi

if [[ -z "${POSTGRES_ADMIN_PASSWORD:-}" ]]; then
  if [[ -t 0 ]]; then
    read -r -s -p "PostgreSQL administrator password: " POSTGRES_ADMIN_PASSWORD
    printf '\n'
    export POSTGRES_ADMIN_PASSWORD
  else
    fail "POSTGRES_ADMIN_PASSWORD must be set for noninteractive deployment."
  fi
fi

[[ -n "$POSTGRES_ADMIN_PASSWORD" ]] ||
  fail "POSTGRES_ADMIN_PASSWORD cannot be empty."

log "Reading ACR information from the shared deployment"

ACR_NAME="$(
  az deployment group show \
    --name "$SHARED_DEPLOYMENT_NAME" \
    --resource-group "$SHARED_RESOURCE_GROUP" \
    --query properties.outputs.acrName.value \
    --output tsv
)"

ACR_LOGIN_SERVER="$(
  az deployment group show \
    --name "$SHARED_DEPLOYMENT_NAME" \
    --resource-group "$SHARED_RESOURCE_GROUP" \
    --query properties.outputs.acrLoginServer.value \
    --output tsv
)"

[[ -n "$ACR_NAME" ]] ||
  fail "Could not read acrName from shared deployment '$SHARED_DEPLOYMENT_NAME'."

[[ -n "$ACR_LOGIN_SERVER" ]] ||
  fail "Could not read acrLoginServer from shared deployment '$SHARED_DEPLOYMENT_NAME'."

log "Using registry: $ACR_LOGIN_SERVER"

if [[ -n "${IMAGE_TAG:-}" ]]; then
  RESOLVED_IMAGE_TAG="$IMAGE_TAG"
elif git -C "$REPOSITORY_ROOT" rev-parse --verify HEAD >/dev/null 2>&1; then
  RESOLVED_IMAGE_TAG="$(
    git -C "$REPOSITORY_ROOT" rev-parse --short=12 HEAD
  )"
else
  RESOLVED_IMAGE_TAG="$(date -u +'%Y%m%d%H%M%S')"
fi

BACKEND_IMAGE="${BACKEND_IMAGE:-${ACR_LOGIN_SERVER}/${BACKEND_IMAGE_REPOSITORY}:${RESOLVED_IMAGE_TAG}}"


export BACKEND_IMAGE

export POSTGRES_ADMIN_PASSWORD

log "Using backend image: $BACKEND_IMAGE"

if [[ "$SKIP_IMAGE_BUILD" != "true" ]]; then
  log "Logging in to Azure Container Registry"

  az acr login \
    --name "$ACR_NAME"

  log "Building and pushing backend image"
  printf 'Image: %s\n' "$BACKEND_IMAGE"

  docker buildx build \
    --platform linux/amd64 \
    --file "$BACKEND_DOCKERFILE" \
    --tag "$BACKEND_IMAGE" \
    --push \
    "$BACKEND_BUILD_CONTEXT"
else
  [[ -n "${BACKEND_IMAGE:-}" ]] ||
    fail "BACKEND_IMAGE must be supplied when SKIP_IMAGE_BUILD=true."

  log "Skipping image build; using $BACKEND_IMAGE"
fi

log "Verifying backend image exists in ACR"

az acr repository show \
  --name "$ACR_NAME" \
  --image "${BACKEND_IMAGE_REPOSITORY}:${RESOLVED_IMAGE_TAG}" \
  --output none

log "Ensuring environment resource group exists: $ENVIRONMENT_RESOURCE_GROUP"

az group create \
  --name "$ENVIRONMENT_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --tags \
    application=realty \
    environment="$ENVIRONMENT" \
    scope=environment \
    managedBy=bicep \
  --output none

log "Compiling environment Bicep template"

az bicep build \
  --file "$ENVIRONMENT_TEMPLATE" \
  --stdout \
  >/dev/null

log "Validating $ENVIRONMENT infrastructure"

az deployment group validate \
  --name "${DEPLOYMENT_NAME}-validate" \
  --resource-group "$ENVIRONMENT_RESOURCE_GROUP" \
  --template-file "$ENVIRONMENT_TEMPLATE" \
  --parameters \
    "$ENVIRONMENT_PARAMETERS" \
    backendImage="$BACKEND_IMAGE" \
    postgresAdminPassword="$POSTGRES_ADMIN_PASSWORD" \
  --output none

log "Previewing $ENVIRONMENT infrastructure changes"

az deployment group what-if \
  --name "${DEPLOYMENT_NAME}-what-if" \
  --resource-group "$ENVIRONMENT_RESOURCE_GROUP" \
  --template-file "$ENVIRONMENT_TEMPLATE" \
  --parameters \
    "$ENVIRONMENT_PARAMETERS" \
    backendImage="$BACKEND_IMAGE" \
    postgresAdminPassword="$POSTGRES_ADMIN_PASSWORD"

if [[ "${AUTO_APPROVE:-false}" != "true" ]]; then
  printf '\nDeploy these %s infrastructure changes? [y/N] ' "$ENVIRONMENT"
  read -r answer

  case "$answer" in
    y | Y | yes | YES)
      ;;
    *)
      log "Deployment cancelled"
      exit 0
      ;;
  esac
fi

log "Deploying $ENVIRONMENT infrastructure"

az deployment group create \
  --name "$DEPLOYMENT_NAME" \
  --resource-group "$ENVIRONMENT_RESOURCE_GROUP" \
  --template-file "$ENVIRONMENT_TEMPLATE" \
  --parameters \
    "$ENVIRONMENT_PARAMETERS" \
    backendImage="$BACKEND_IMAGE" \
    postgresAdminPassword="$POSTGRES_ADMIN_PASSWORD" \
  --output none

log "Reading deployment outputs"

DEPLOYMENT_OUTPUTS="$(
  az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$ENVIRONMENT_RESOURCE_GROUP" \
    --query properties.outputs \
    --output json
)"

printf '%s\n' "$DEPLOYMENT_OUTPUTS"

if [[ "$RUN_JOBS" == "true" ]]; then
  OLLAMA_BOOTSTRAP_JOB_NAME="$(
    az deployment group show \
      --name "$DEPLOYMENT_NAME" \
      --resource-group "$ENVIRONMENT_RESOURCE_GROUP" \
      --query properties.outputs.ollamaBootstrapJobName.value \
      --output tsv
  )"

  MIGRATION_JOB_NAME="$(
    az deployment group show \
      --name "$DEPLOYMENT_NAME" \
      --resource-group "$ENVIRONMENT_RESOURCE_GROUP" \
      --query properties.outputs.migrationJobName.value \
      --output tsv
  )"

  [[ -n "$OLLAMA_BOOTSTRAP_JOB_NAME" ]] ||
    fail "Deployment did not return ollamaBootstrapJobName."

  [[ -n "$MIGRATION_JOB_NAME" ]] ||
    fail "Deployment did not return migrationJobName."

  log "Starting Ollama bootstrap job: $OLLAMA_BOOTSTRAP_JOB_NAME"

  OLLAMA_EXECUTION="$(
    az containerapp job start \
      --name "$OLLAMA_BOOTSTRAP_JOB_NAME" \
      --resource-group "$ENVIRONMENT_RESOURCE_GROUP" \
      --query name \
      --output tsv
  )"

  log "Ollama execution started: $OLLAMA_EXECUTION"
  log "Waiting for Ollama bootstrap job"

  wait_for_job_execution \
    "$OLLAMA_BOOTSTRAP_JOB_NAME" \
    "$OLLAMA_EXECUTION"

  log "Starting database migration job: $MIGRATION_JOB_NAME"

  MIGRATION_EXECUTION="$(
    az containerapp job start \
      --name "$MIGRATION_JOB_NAME" \
      --resource-group "$ENVIRONMENT_RESOURCE_GROUP" \
      --query name \
      --output tsv
  )"

  log "Migration execution started: $MIGRATION_EXECUTION"
  log "Waiting for database migration job"

  wait_for_job_execution \
    "$MIGRATION_JOB_NAME" \
    "$MIGRATION_EXECUTION"
fi

BACKEND_URL="$(
  az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$ENVIRONMENT_RESOURCE_GROUP" \
    --query properties.outputs.backendUrl.value \
    --output tsv
)"

log "$ENVIRONMENT deployment succeeded"
printf 'Backend image: %s\n' "$BACKEND_IMAGE"
printf 'Backend URL:   %s\n' "$BACKEND_URL"