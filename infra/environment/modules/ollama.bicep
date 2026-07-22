@description('Name of the Ollama Container App')
param appName string

@description('Resource ID of the existing Container Apps environment')
param containerAppsEnvironmentId string

@description('Name of the existing Container Apps environment')
param containerAppsEnvironmentName string

@description('Azure region')
param location string = resourceGroup().location

@description('Pinned Ollama image')
param ollamaImage string

@description('Storage account name used for Ollama model persistence')
@minLength(3)
@maxLength(24)
param storageAccountName string

@description('Azure Files share name')
param fileShareName string = 'ollama-models'

@description('Storage registration name in the Container Apps environment')
param environmentStorageName string = 'ollama-storage'

@description('CPU cores allocated to Ollama')
@allowed([
  2
  4
])
param cpu int = 2

@description('Memory allocated to Ollama')
@allowed([
  '4Gi'
  '8Gi'
])
param memory string = '4Gi'

@description('Minimum number of Ollama replicas')
@minValue(1)
param minReplicas int = 1

@description('Maximum number of Ollama replicas')
@minValue(1)
param maxReplicas int = 1

@description('Tags applied to Ollama resources')
param tags object = {}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2026-01-01' existing = {
  name: containerAppsEnvironmentName
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-06-01' = {
  name: storageAccountName
  location: location
  tags: tags

  sku: {
    name: 'Standard_LRS'
  }

  kind: 'StorageV2'

  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2025-06-01' = {
  parent: storageAccount
  name: 'default'
}

resource fileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2025-06-01' = {
  parent: fileService
  name: fileShareName

  properties: {
    accessTier: 'TransactionOptimized'
    enabledProtocols: 'SMB'
    shareQuota: 100
  }
}

resource environmentStorage 'Microsoft.App/managedEnvironments/storages@2026-01-01' = {
  parent: containerAppsEnvironment
  name: environmentStorageName

  properties: {
    azureFile: {
      accountName: storageAccount.name
      accountKey: storageAccount.listKeys().keys[0].value
      shareName: fileShare.name
      accessMode: 'ReadWrite'
    }
  }
}

resource ollamaApp 'Microsoft.App/containerApps@2026-01-01' = {
  name: appName
  location: location
  tags: tags

  properties: {
    managedEnvironmentId: containerAppsEnvironmentId
    workloadProfileName: 'Consumption'

    configuration: {
      activeRevisionsMode: 'Single'

      ingress: {
        external: false
        allowInsecure: false
        targetPort: 11434
        transport: 'http'

        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
    }

    template: {
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }

      containers: [
        {
          name: 'ollama'
          image: ollamaImage

          env: [
            {
              name: 'OLLAMA_HOST'
              value: '0.0.0.0:11434'
            }
            {
              name: 'OLLAMA_MAX_LOADED_MODELS'
              value: '1'
            }
            {
              name: 'OLLAMA_NUM_PARALLEL'
              value: '1'
            }
          ]

          resources: {
            cpu: cpu
            memory: memory
          }

          volumeMounts: [
            {
              volumeName: 'ollama-models'
              mountPath: '/root/.ollama'
            }
          ]

          probes: [
            {
              type: 'Startup'

              tcpSocket: {
                port: 11434
              }

              initialDelaySeconds: 5
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 30
            }
            {
              type: 'Liveness'

              tcpSocket: {
                port: 11434
              }

              periodSeconds: 30
              timeoutSeconds: 5
              failureThreshold: 3
            }
            {
              type: 'Readiness'

              tcpSocket: {
                port: 11434
              }

              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 3
            }
          ]
        }
      ]

      volumes: [
        {
          name: 'ollama-models'
          storageType: 'AzureFile'
          storageName: environmentStorage.name
        }
      ]
    }
  }
}

output appId string = ollamaApp.id
output appName string = ollamaApp.name
output internalFqdn string = ollamaApp.properties.configuration.ingress.fqdn
output storageAccountId string = storageAccount.id
output fileShareName string = fileShare.name
