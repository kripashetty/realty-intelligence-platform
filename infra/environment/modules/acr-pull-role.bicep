targetScope = 'resourceGroup'

@description('Name of the existing Azure Container Registry')
param acrName string

@description('Principal ID receiving the AcrPull role')
param principalId string

var acrPullRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '7f951dda-4ed3-4680-a7ca-43fe172d538d'
)

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource acrPullAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(
    acr.id,
    principalId,
    acrPullRoleDefinitionId
  )
  scope: acr

  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPullRoleDefinitionId
  }
}

output acrId string = acr.id
output loginServer string = acr.properties.loginServer
