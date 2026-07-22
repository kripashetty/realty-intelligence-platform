using '../main.bicep'

param location = 'northeurope'
param sharedResourceGroupName = 'realty-shared-rg'
param environmentResourceGroupName = 'realty-dev-rg'

param tags = {
  application: 'realty'
  environment: 'dev'
  managedBy: 'bicep'
}
