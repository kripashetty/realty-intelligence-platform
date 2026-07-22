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

RESOURCE_GROUP="${RESOURCE_GROUP:-realty-${ENVIRONMENT}-rg}"
DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-realty-${ENVIRONMENT}}"
FRONTEND_DIR="${FRONTEND_DIR:-${REPOSITORY_ROOT}/frontend}"
FRONTEND_OUTPUT_DIR="${FRONTEND_OUTPUT_DIR:-${FRONTEND_DIR}/dist}"

log() {
  printf '[%s] %s\n' \
    "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    "$*"
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 ||
    fail "Required command '$1' is not installed."
}

require_command az
require_command npm
require_command swa
require_command curl

az account show >/dev/null 2>&1 ||
  fail "Not signed in to Azure. Run: az login"

[[ -d "$FRONTEND_DIR" ]] ||
  fail "Frontend directory not found: $FRONTEND_DIR"

log "Reading environment deployment outputs"

FRONTEND_NAME="$(
  az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.outputs.frontendName.value \
    --output tsv
)"

FRONTEND_URL="$(
  az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.outputs.frontendUrl.value \
    --output tsv
)"

CORS_ORIGINS="$(
  az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.outputs.frontendUrl.value \
    --output tsv
)"

BACKEND_URL="$(
  az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.outputs.backendUrl.value \
    --output tsv
)"

[[ -n "$FRONTEND_NAME" ]] ||
  fail "frontendName deployment output is empty."

[[ -n "$FRONTEND_URL" ]] ||
  fail "frontendUrl deployment output is empty."

[[ -n "$BACKEND_URL" ]] ||
  fail "backendUrl deployment output is empty."

log "Static Web App: $FRONTEND_NAME"
log "Backend URL: $BACKEND_URL"

log "Retrieving Static Web Apps deployment token"

SWA_DEPLOYMENT_TOKEN="$(
  az staticwebapp secrets list \
    --name "$FRONTEND_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.apiKey \
    --output tsv
)"

[[ -n "$SWA_DEPLOYMENT_TOKEN" ]] ||
  fail "Could not retrieve the Static Web Apps deployment token."

export VITE_API_BASE_URL="${BACKEND_URL%/}/api/v1"
log "Frontend API base URL: $VITE_API_BASE_URL"

log "Installing frontend dependencies"

npm --prefix "$FRONTEND_DIR" ci

log "Building frontend"

npm --prefix "$FRONTEND_DIR" run build

[[ -f "${FRONTEND_OUTPUT_DIR}/index.html" ]] ||
  fail "Frontend build did not produce ${FRONTEND_OUTPUT_DIR}/index.html."

log "Deploying frontend"

swa deploy "$FRONTEND_OUTPUT_DIR" \
  --deployment-token "$SWA_DEPLOYMENT_TOKEN" \
  --env production

unset SWA_DEPLOYMENT_TOKEN

log "Verifying frontend URL"

for attempt in $(seq 1 30); do
  if curl \
    --fail \
    --silent \
    --show-error \
    "$FRONTEND_URL" > /dev/null; then
    log "Frontend is reachable."
    printf 'Frontend URL: %s\n' "$FRONTEND_URL"
    exit 0
  fi

  log "Frontend is not ready yet; attempt ${attempt}/30"
  sleep 5
done

fail "Frontend did not become reachable: $FRONTEND_URL"