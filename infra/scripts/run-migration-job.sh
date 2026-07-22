#!/usr/bin/env bash

set -Eeuo pipefail

JOB_NAME="${JOB_NAME:-realty-dev-migrate}"
RESOURCE_GROUP="${DEV_RESOURCE_GROUP:-${RESOURCE_GROUP:-realty-dev-rg}}"
CONTAINER_NAME="${CONTAINER_NAME:-migration}"

POLL_SECONDS="${POLL_SECONDS:-5}"
REPLICA_WAIT_SECONDS="${REPLICA_WAIT_SECONDS:-120}"
EXECUTION_TIMEOUT_SECONDS="${EXECUTION_TIMEOUT_SECONDS:-2100}"

log() {
  printf '[%s] %s\n' \
    "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    "$*"
}

fail() {
  printf '\nERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 ||
    fail "Required command '$1' is not installed."
}

require_command az
require_command python3

az account show >/dev/null 2>&1 ||
  fail "Not signed in to Azure. Run: az login"

get_status() {
  az containerapp job execution show \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --job-execution-name "$EXECUTION_NAME" \
    --query properties.status \
    --output tsv 2>/dev/null || true
}

get_replicas_json() {
  az containerapp job replica list \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --execution "$EXECUTION_NAME" \
    --output json 2>/dev/null || printf '[]'
}

get_replica_count() {
  get_replicas_json |
    python3 -c '
import json
import sys

try:
    value = json.load(sys.stdin)
    print(len(value) if isinstance(value, list) else 0)
except Exception:
    print(0)
'
}

collect_diagnostics() {
  printf '\n=== Execution details ===\n'

  az containerapp job execution show \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --job-execution-name "$EXECUTION_NAME" \
    --output jsonc || true

  printf '\n=== Replica details ===\n'

  az containerapp job replica list \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --execution "$EXECUTION_NAME" \
    --output jsonc || true

  printf '\n=== Deployed migration container ===\n'

  az containerapp job show \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.template.containers[0].{
      image:image,
      command:command,
      args:args,
      env:env,
      resources:resources
    }" \
    --output jsonc || true

  printf '\n=== Registry configuration ===\n'

  az containerapp job show \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.configuration.registries \
    --output jsonc || true

  printf '\n=== Secret references ===\n'

  az containerapp job show \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.configuration.secrets \
    --output jsonc || true

  printf '\n=== Managed identity ===\n'

  az containerapp job show \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query identity \
    --output jsonc || true
}

query_log_analytics() {
  local environment_id
  local environment_name
  local workspace_id

  environment_id="$(
    az containerapp job show \
      --name "$JOB_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --query properties.environmentId \
      --output tsv 2>/dev/null || true
  )"

  environment_name="${environment_id##*/}"

  if [[ -z "$environment_name" ]]; then
    log "Could not determine the Container Apps environment."
    return 1
  fi

  workspace_id="$(
    az containerapp env show \
      --name "$environment_name" \
      --resource-group "$RESOURCE_GROUP" \
      --query properties.appLogsConfiguration.logAnalyticsConfiguration.customerId \
      --output tsv 2>/dev/null || true
  )"

  if [[ -z "$workspace_id" || "$workspace_id" == "null" ]]; then
    log "No Log Analytics workspace is configured for this environment."
    return 1
  fi

  log "Querying Log Analytics workspace: $workspace_id"

  printf '\n=== Historical console logs ===\n'

  if az monitor log-analytics query \
    --workspace "$workspace_id" \
    --analytics-query "
      ContainerAppConsoleLogs_CL
      | where TimeGenerated > ago(2h)
      | where JobName_s == '${JOB_NAME}'
          or ContainerName_s == '${CONTAINER_NAME}'
          or Log_s contains '${EXECUTION_NAME}'
      | project
          TimeGenerated,
          JobName_s,
          ContainerName_s,
          RevisionName_s,
          Log_s
      | order by TimeGenerated asc
    " \
    --output table; then
    return 0
  fi

  log "Legacy console-log schema failed; trying the newer schema."

  az monitor log-analytics query \
    --workspace "$workspace_id" \
    --analytics-query "
      ContainerAppConsoleLogs
      | where TimeGenerated > ago(2h)
      | where JobName == '${JOB_NAME}'
          or ContainerName == '${CONTAINER_NAME}'
          or Log contains '${EXECUTION_NAME}'
      | project
          TimeGenerated,
          JobName,
          ContainerName,
          RevisionName,
          Log
      | order by TimeGenerated asc
    " \
    --output table || true

  printf '\n=== Historical system logs ===\n'

  if az monitor log-analytics query \
    --workspace "$workspace_id" \
    --analytics-query "
      ContainerAppSystemLogs_CL
      | where TimeGenerated > ago(2h)
      | where Log_s contains '${JOB_NAME}'
          or Log_s contains '${EXECUTION_NAME}'
      | project
          TimeGenerated,
          Type_s,
          Reason_s,
          Log_s
      | order by TimeGenerated asc
    " \
    --output table; then
    return 0
  fi

  log "Legacy system-log schema failed; trying the newer schema."

  az monitor log-analytics query \
    --workspace "$workspace_id" \
    --analytics-query "
      ContainerAppSystemLogs
      | where TimeGenerated > ago(2h)
      | where Log contains '${JOB_NAME}'
          or Log contains '${EXECUTION_NAME}'
      | project
          TimeGenerated,
          Type,
          Reason,
          Log
      | order by TimeGenerated asc
    " \
    --output table || true
}

LOG_PID=""

cleanup() {
  if [[ -n "$LOG_PID" ]]; then
    kill "$LOG_PID" >/dev/null 2>&1 || true
    wait "$LOG_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

log "Using migration job: $JOB_NAME"
log "Using resource group: $RESOURCE_GROUP"

log "Current migration job configuration"

az containerapp job show \
  --name "$JOB_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "{
    environmentId:properties.environmentId,
    identity:identity,
    registries:properties.configuration.registries,
    secrets:properties.configuration.secrets,
    container:properties.template.containers[0]
  }" \
  --output jsonc

log "Starting migration execution"

EXECUTION_NAME="$(
  az containerapp job start \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query name \
    --output tsv
)"

[[ -n "$EXECUTION_NAME" ]] ||
  fail "Azure did not return an execution name."

log "Execution started: $EXECUTION_NAME"
log "Waiting for a replica to appear"

elapsed=0
replica_found=false

while (( elapsed < REPLICA_WAIT_SECONDS )); do
  status="$(get_status)"
  replica_count="$(get_replica_count)"

  log "Status=${status:-Pending}; replicas=$replica_count"

  if (( replica_count > 0 )); then
    replica_found=true
    break
  fi

  case "$status" in
    Succeeded | Failed)
      break
      ;;
  esac

  sleep "$POLL_SECONDS"
  elapsed=$((elapsed + POLL_SECONDS))
done

if [[ "$replica_found" == "true" ]]; then
  log "Replica found. Attempting live console-log streaming."

  az containerapp job logs show \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --execution "$EXECUTION_NAME" \
    --container "$CONTAINER_NAME" \
    --follow &

  LOG_PID=$!
else
  log "No replica was visible through the preview replica API."
fi

log "Monitoring migration execution"

elapsed=0

while (( elapsed < EXECUTION_TIMEOUT_SECONDS )); do
  status="$(get_status)"

  log "Execution status: ${status:-Pending}"

  case "$status" in
    Succeeded)
      cleanup
      LOG_PID=""
      log "Migration execution succeeded."
      exit 0
      ;;

    Failed)
      cleanup
      LOG_PID=""

      log "Migration execution failed."

      collect_diagnostics
      query_log_analytics || true

      exit 1
      ;;
  esac

  sleep "$POLL_SECONDS"
  elapsed=$((elapsed + POLL_SECONDS))
done

cleanup
LOG_PID=""

log "Timed out waiting for the migration execution."

collect_diagnostics
query_log_analytics || true

exit 1