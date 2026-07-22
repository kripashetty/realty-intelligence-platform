using '../main.bicep'

param environment = 'prod'
param location = 'germanywestcentral'
param postgresAdminLogin = 'realtyadmin'
param backendImage = 'DEPLOYMENT_WORKFLOW_MUST_OVERRIDE_THIS'
param ollamaImage = 'ollama/ollama:<PINNED_VERSION>'
param acrName = 'YOUR_SHARED_ACR_NAME'
param acrResourceGroupName = 'realty-shared-rg'

param tags = {
  application: 'realty'
  environment: 'prod'
  managedBy: 'bicep'
  workload: 'portfolio'
}
