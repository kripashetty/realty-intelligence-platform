@description('Name of the Container Apps environment')
param environmentName string

@description('Azure region')
param location string = resourceGroup().location

@description('Tags applied to resources')
param tags object = {}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2026-01-01' = {
  name: environmentName
  location: location
  tags: tags

  properties: {
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]

    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
  }
}

output environmentId string = containerAppsEnvironment.id
output environmentName string = containerAppsEnvironment.name
