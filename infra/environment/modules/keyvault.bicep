@description('Name of the Key Vault')
param vaultName string

@description('Azure region')
param location string = resourceGroup().location

@description('Microsoft Entra tenant ID')
param tenantId string = subscription().tenantId

@description('Object ID of the backend user-assigned managed identity')
param backendPrincipalObjectId string

@description('Database connection URL')
@secure()
param databaseUrl string

@description('Enable purge protection')
param enablePurgeProtection bool = false

@description('Number of days soft-deleted objects are retained')
@minValue(7)
@maxValue(90)
param softDeleteRetentionDays int = 7

@description('Whether Key Vault exposes a public endpoint')
@allowed([
  'Enabled'
  'Disabled'
])
param publicNetworkAccess string = 'Enabled'

@description('Tags applied to Key Vault resources')
param tags object = {}

var databaseUrlSecretName = 'database-url'

var keyVaultSecretsUserRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '4633458b-17de-408a-b874-0445c86b69e6'
)

resource keyVault 'Microsoft.KeyVault/vaults@2026-02-01' = {
  name: vaultName
  location: location
  tags: tags

  properties: union(

    {

      tenantId: tenantId

      sku: {

        family: 'A'

        name: 'standard'

      }

      enableRbacAuthorization: true

      accessPolicies: []

      enableSoftDelete: true

      softDeleteRetentionInDays: softDeleteRetentionDays

      publicNetworkAccess: publicNetworkAccess

      networkAcls: {

        bypass: 'AzureServices'

        defaultAction: 'Allow'

        ipRules: []

        virtualNetworkRules: []

      }

    },

    enablePurgeProtection

      ? {

          enablePurgeProtection: true

        }

      : {}

  )
}

resource backendSecretsUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(
    keyVault.id,
    backendPrincipalObjectId,
    keyVaultSecretsUserRoleDefinitionId
  )
  scope: keyVault

  properties: {
    principalId: backendPrincipalObjectId
    principalType: 'ServicePrincipal'
    roleDefinitionId: keyVaultSecretsUserRoleDefinitionId
  }
}

resource databaseUrlSecret 'Microsoft.KeyVault/vaults/secrets@2026-02-01' = {
  parent: keyVault
  name: databaseUrlSecretName

  properties: {
    value: databaseUrl
    contentType: 'PostgreSQL SQLAlchemy connection URL'
  }
}

output vaultId string = keyVault.id
output vaultName string = keyVault.name
output vaultUri string = keyVault.properties.vaultUri

// Versionless URI lets Container Apps resolve the current secret version.
output databaseUrlSecretUri string = '${keyVault.properties.vaultUri}secrets/${databaseUrlSecret.name}'
