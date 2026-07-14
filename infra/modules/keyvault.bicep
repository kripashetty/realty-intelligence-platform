@description('Name of the Key Vault')
param vaultName string

@description('Azure region')
param location string = resourceGroup().location

@description('Tenant ID')
param tenantId string = subscription().tenantId

@description('Object ID of the Container Apps managed identity to grant secret read access')
param principalObjectId string

@description('Database connection string')
@secure()
param databaseUrl string

@description('Ollama service URL')
param ollamaUrl string

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: vaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: tenantId
    enableSoftDelete: true
    softDeleteRetentionDays: 7
    enableRbacAuthorization: false
    accessPolicies: [
      {
        tenantId: tenantId
        objectId: principalObjectId
        permissions: {
          secrets: ['get', 'list']
        }
      }
    ]
  }
}

resource secretDatabaseUrl 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'DATABASE-URL'
  properties: {
    value: databaseUrl
  }
}

resource secretOllamaUrl 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'OLLAMA-URL'
  properties: {
    value: ollamaUrl
  }
}

output vaultUri string = keyVault.properties.vaultUri
