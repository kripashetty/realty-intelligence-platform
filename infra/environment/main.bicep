targetScope = 'resourceGroup'

@description('Environment name')
@allowed([
  'dev'
  'prod'
])
param environment string

@description('Azure region')
param location string = resourceGroup().location

@description('PostgreSQL administrator login')
param postgresAdminLogin string

@description('PostgreSQL administrator password')
@secure()
param postgresAdminPassword string

@description('Immutable backend image reference, preferably tagged with a Git commit SHA')
param backendImage string

@description('Pinned Ollama container image')
param ollamaImage string

@description('Name of the shared Azure Container Registry')
param acrName string

@description('Resource group containing the shared Azure Container Registry')
param acrResourceGroupName string

@description('Subscription containing the shared Azure Container Registry')
param acrSubscriptionId string = subscription().subscriptionId

@description('Ollama model installed by the bootstrap job')

param ollamaModel string

@description('Azure region for Static Web Apps')

param frontendLocation string = 'westeurope'


@description('Tags applied to environment resources')
param tags object = {
  application: 'realty'
  environment: environment
  managedBy: 'bicep'
}

var prefix = 'realty-${environment}'

var uniqueSuffix = uniqueString(
  subscription().subscriptionId,
  resourceGroup().id,
  environment
)

var postgresServerName = take(
  '${prefix}-pg-${uniqueSuffix}',
  63
)

var keyVaultName = take(
  '${prefix}-kv-${uniqueSuffix}',
  24
)

var containerAppsEnvironmentName = '${prefix}-cae'
var backendAppName = '${prefix}-backend'
var ollamaAppName = '${prefix}-ollama'
var backendIdentityName = '${prefix}-backend-id'

var ollamaStorageAccountName = take(
  toLower('realty${environment}ollama${uniqueSuffix}'),
  24
)

var databaseName = 'realty'

// Transitional design.
//
// This value is passed directly into Key Vault and is never exposed
// as a deployment output. A later improvement is to store the password
// separately and construct the SQLAlchemy URL inside Python.
var databaseUrl = 'postgresql+asyncpg://${postgresAdminLogin}:${postgresAdminPassword}@${postgresql.outputs.serverFqdn}:5432/${databaseName}?ssl=require'


var migrationJobName = '${prefix}-migrate'
var ollamaBootstrapJobName = '${prefix}-ollama-bootstrap'

var frontendAppName = '${prefix}-frontend'

var corsOrigins = environment == 'prod'
  ? frontend.outputs.frontendUrl
  : 'http://localhost:3000,http://localhost:5173,${frontend.outputs.frontendUrl}'


resource backendIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: backendIdentityName
  location: location
  tags: union(tags, {
    component: 'backend-identity'
  })
}

module postgresql 'modules/postgresql.bicep' = {
  name: 'postgresql-${environment}'

  params: {
    serverName: postgresServerName
    databaseName: databaseName
    administratorLogin: postgresAdminLogin
    administratorLoginPassword: postgresAdminPassword
    location: location

    skuName: environment == 'prod'
      ? 'Standard_D2s_v3'
      : 'Standard_B1ms'

    skuTier: environment == 'prod'
      ? 'GeneralPurpose'
      : 'Burstable'

    storageSizeGB: environment == 'prod'
      ? 128
      : 32

    backupRetentionDays: environment == 'prod'
      ? 14
      : 7

    publicNetworkAccess: 'Enabled'

    tags: union(tags, {
      component: 'database'
    })
  }
}

module containerAppsEnvironment 'modules/container-apps-environment.bicep' = {
  name: 'container-apps-environment-${environment}'

  params: {
    environmentName: containerAppsEnvironmentName
    location: location

    tags: union(tags, {
      component: 'container-apps-environment'
    })
  }
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'key-vault-${environment}'

  params: {
    vaultName: keyVaultName
    location: location
    backendPrincipalObjectId: backendIdentity.properties.principalId
    databaseUrl: databaseUrl
    enablePurgeProtection: environment == 'prod'
    publicNetworkAccess: 'Enabled'

    tags: union(tags, {
      component: 'secrets'
    })
  }
}

// This module deploys the AcrPull role assignment into the shared
// ACR resource group, avoiding the cross-scope BCP139 error.
module backendAcrPull 'modules/acr-pull-role.bicep' = {
  name: 'backend-acr-pull-${environment}'

  scope: resourceGroup(
    acrSubscriptionId,
    acrResourceGroupName
  )

  params: {
    acrName: acrName
    principalId: backendIdentity.properties.principalId
  }
}

module migrationJob 'modules/migration-job.bicep' = {
  name: 'migration-job-${environment}'

  params: {
    jobName: migrationJobName
    containerAppsEnvironmentId: containerAppsEnvironment.outputs.environmentId
    location: location

    backendImage: backendImage
    acrLoginServer: backendAcrPull.outputs.loginServer
    workloadIdentityResourceId: backendIdentity.id
    databaseUrlSecretUri: keyVault.outputs.databaseUrlSecretUri

    replicaTimeout: 1800
    replicaRetryLimit: 1

    tags: union(tags, {
      component: 'database-migration'
    })
  }
}

module ollama 'modules/ollama.bicep' = {
  name: 'ollama-${environment}'

  params: {
    appName: ollamaAppName
    containerAppsEnvironmentId: containerAppsEnvironment.outputs.environmentId
    containerAppsEnvironmentName: containerAppsEnvironment.outputs.environmentName
    location: location
    ollamaImage: ollamaImage

    // This expression always has a "realty" prefix and therefore
    // satisfies Azure Storage's minimum length requirement.
    storageAccountName: ollamaStorageAccountName
    fileShareName: 'ollama-models'
    environmentStorageName: 'ollama-storage'
    cpu: environment == 'prod' ? 4 : 2
    memory: environment == 'prod' ? '8Gi' : '4Gi'

    minReplicas: 1
    maxReplicas: 1

    tags: union(tags, {
      component: 'ollama'
    })
  }
}

module ollamaBootstrapJob 'modules/ollama-bootstrap-job.bicep' = {
  name: 'ollama-bootstrap-job-${environment}'

  params: {
    jobName: ollamaBootstrapJobName
    containerAppsEnvironmentId: containerAppsEnvironment.outputs.environmentId
    location: location

    ollamaUrl: 'https://${ollama.outputs.internalFqdn}'
    ollamaModel: ollamaModel

    // Keep this pinned rather than using latest.
    curlImage: 'curlimages/curl:8.14.1'

    replicaTimeout: 3600
    replicaRetryLimit: 1

    tags: union(tags, {
      component: 'ollama-bootstrap'
    })
  }
}

module frontend 'modules/static-web-app.bicep' = {
  name: 'frontend-${environment}'
  params: {
    staticWebAppName: frontendAppName
    location: frontendLocation
    skuName: environment == 'prod' ? 'Standard' : 'Free'
    tags: union(tags, {
      component: 'frontend'
    })
  }
}

module backend 'modules/container-apps.bicep' = {
  name: 'backend-${environment}'

  params: {
    backendAppName: backendAppName
    containerAppsEnvironmentId: containerAppsEnvironment.outputs.environmentId
    location: location
    backendImage: backendImage
    corsOrigins: corsOrigins
    acrLoginServer: backendAcrPull.outputs.loginServer
    workloadIdentityResourceId: backendIdentity.id
    databaseUrlSecretUri: keyVault.outputs.databaseUrlSecretUri
    ollamaUrl: 'https://${ollama.outputs.internalFqdn}'
    ollamaModel: ollamaModel
    minReplicas: environment == 'prod'
      ? 1
      : 0

    maxReplicas: environment == 'prod'
      ? 5
      : 2

    concurrentRequestsPerReplica: 50

    tags: union(tags, {
      component: 'backend'
    })
  }
}



output backendUrl string = backend.outputs.backendUrl
output ollamaInternalFqdn string = ollama.outputs.internalFqdn

output postgresFqdn string = postgresql.outputs.serverFqdn
output postgresDatabaseName string = postgresql.outputs.databaseName



output keyVaultUri string = keyVault.outputs.vaultUri 


output backendIdentityId string = backendIdentity.id
output backendIdentityPrincipalId string = backendIdentity.properties.principalId

output containerAppsEnvironmentId string = containerAppsEnvironment.outputs.environmentId

output migrationJobName string = migrationJob.outputs.jobName
output ollamaBootstrapJobName string = ollamaBootstrapJob.outputs.jobName
output ollamaModel string = ollamaModel

output frontendName string = frontend.outputs.staticWebAppName
output frontendUrl string = frontend.outputs.frontendUrl



// output backendUrl string = backend.outputs.backendUrl
// output migrationJobName string = migrationJob.outputs.jobName
// output ollamaBootstrapJobName string = ollamaBootstrapJob.outputs.jobName

// output containerAppsEnvironmentId string =
//   containerAppsEnvironment.outputs.environmentId

// output backendIdentityId string = backendIdentity.id
// output keyVaultUri string = keyVault.outputs.keyVaultUri

