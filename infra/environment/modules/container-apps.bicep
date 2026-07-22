@description('Name of the backend Container App')
param backendAppName string

@description('Resource ID of the existing Container Apps environment')
param containerAppsEnvironmentId string

@description('Azure region')
param location string = resourceGroup().location

@description('Immutable backend image reference')
param backendImage string

@description('Azure Container Registry login server')
param acrLoginServer string

@description('Resource ID of the user-assigned managed identity')
param workloadIdentityResourceId string

@description('Versionless Key Vault URI for the database URL secret')
param databaseUrlSecretUri string

@description('Internal URL of the Ollama service')
param ollamaUrl string

@description('Ollama model used by the backend')
param ollamaModel string

@description('Minimum backend replica count')
@minValue(0)
param minReplicas int = 0

@description('Maximum backend replica count')
@minValue(1)
param maxReplicas int = 2

@description('Concurrent HTTP requests per replica before scaling')
@minValue(1)
param concurrentRequestsPerReplica int = 50

@description('Tags applied to the backend Container App')
param tags object = {}

@description('Comma-separated CORS origins')
param corsOrigins string

resource backendApp 'Microsoft.App/containerApps@2026-01-01' = {
  name: backendAppName
  location: location
  tags: tags

  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${workloadIdentityResourceId}': {}
    }
  }

  properties: {
    managedEnvironmentId: containerAppsEnvironmentId
    workloadProfileName: 'Consumption'

    configuration: {
      activeRevisionsMode: 'Single'

      ingress: {
        external: true
        allowInsecure: false
        targetPort: 8000
        transport: 'http'

        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }

      registries: [
        {
          server: acrLoginServer
          identity: workloadIdentityResourceId
        }
      ]

      secrets: [
        {
          name: 'database-url'
          keyVaultUrl: databaseUrlSecretUri
          identity: workloadIdentityResourceId
        }
      ]
    }

    template: {
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas

        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: string(concurrentRequestsPerReplica)
              }
            }
          }
        ]
      }

      containers: [
        {
          name: 'backend'
          image: backendImage

          env: [
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'OLLAMA_URL'
              value: ollamaUrl
            }
            {

              name: 'OLLAMA_MODEL'

              value: ollamaModel

            }
            {
              name: 'CORS_ORIGINS'
              value: corsOrigins
            }
          ]

          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }

          probes: [
            {
              type: 'Startup'

              httpGet: {
                path: '/health'
                port: 8000
                scheme: 'HTTP'
              }

              initialDelaySeconds: 2
              periodSeconds: 5
              timeoutSeconds: 3
              failureThreshold: 10
            }
            {
              type: 'Liveness'

              httpGet: {
                path: '/health'
                port: 8000
                scheme: 'HTTP'
              }

              periodSeconds: 20
              timeoutSeconds: 3
              failureThreshold: 3
            }
            {
              type: 'Readiness'

              httpGet: {
                path: '/health'
                port: 8000
                scheme: 'HTTP'
              }

              periodSeconds: 10
              timeoutSeconds: 3
              failureThreshold: 3
            }
          ]
        }
      ]
    }
  }
}

output backendAppId string = backendApp.id
output backendAppName string = backendApp.name
output backendUrl string = 'https://${backendApp.properties.configuration.ingress.fqdn}'
