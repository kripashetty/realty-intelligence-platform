#!/usr/bin/env bash

set -euo pipefail

DEPLOYMENT_NAME="${1:-realty-shared}"
RESOURCE_GROUP="${2:-realty-shared-rg}"

echo "export ACR_ID=\"$(
  az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.outputs.acrId.value" \
    --output tsv
)\""

echo "export ACR_NAME=\"$(
  az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.outputs.acrName.value" \
    --output tsv
)\""

echo "export ACR_LOGIN_SERVER=\"$(
  az deployment group show \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.outputs.acrLoginServer.value" \
    --output tsv
)\""