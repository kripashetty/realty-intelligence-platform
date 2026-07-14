@description('Environment name: dev or prod')
@allowed(['dev', 'prod'])
param environment string

@description('Azure region')
param location string = resourceGroup().location

@description('PostgreSQL administrator login')
param postgresAdminLogin string

@description('PostgreSQL administrator password')
@secure()
param postgresAdminPassword string

@description('Backend container image reference')
param backendImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Azure Container Registry login server')
param acrLoginServer string = ''

@description('Azure Container Registry username')
param acrUsername string = ''

@description('Azure Container Registry password')
@secure()
param acrPassword string = ''

var prefix = 'realty-${environment}'
var postgresServerName = '${prefix}-pg'
var keyVaultName = '${prefix}-kv'
var containerAppsEnvName = '${prefix}-cae'

module postgresql 'modules/postgresql.bicep' = {
  name: 'postgresql'
  params: {
    serverName: postgresServerName
    administratorLogin: postgresAdminLogin
    administratorLoginPassword: postgresAdminPassword
    location: location
    skuName: environment == 'prod' ? 'Standard_D2s_v3' : 'Standard_B1ms'
    storageSizeGB: environment == 'prod' ? 128 : 32
  }
}

module containerApps 'modules/container-apps.bicep' = {
  name: 'containerApps'
  params: {
    environmentName: containerAppsEnvName
    location: location
    backendImage: backendImage
    acrLoginServer: acrLoginServer
    acrUsername: acrUsername
    acrPassword: acrPassword
    databaseUrl: postgresql.outputs.connectionString
    minReplicas: environment == 'prod' ? 2 : 1
    maxReplicas: environment == 'prod' ? 10 : 3
  }
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyVault'
  params: {
    vaultName: keyVaultName
    location: location
    principalObjectId: containerApps.outputs.backendIdentityPrincipalId
    databaseUrl: postgresql.outputs.connectionString
    ollamaUrl: 'http://localhost:11434'
  }
}

output backendUrl string = containerApps.outputs.backendUrl
output postgresServerFqdn string = postgresql.outputs.serverFqdn
output keyVaultUri string = keyVault.outputs.vaultUri
