targetScope = 'resourceGroup'

@description('Azure region for the shared registry')
param location string = resourceGroup().location

@description('Globally unique Azure Container Registry name')
param acrName string

@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param acrSku string = 'Basic'

param tags object = {}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags

  sku: {
    name: acrSku
  }

  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

output acrId string = acr.id
output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
