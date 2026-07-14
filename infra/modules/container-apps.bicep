@description('Name of the Container Apps environment')
param environmentName string

@description('Azure region')
param location string = resourceGroup().location

@description('Backend container image (e.g. myacr.azurecr.io/backend:latest)')
param backendImage string

@description('Azure Container Registry login server')
param acrLoginServer string

@description('Azure Container Registry username')
param acrUsername string

@description('Azure Container Registry password')
@secure()
param acrPassword string

@description('Database connection string (stored as Container App secret)')
@secure()
param databaseUrl string

@description('Enable GPU workload profile (false for MVP CPU-only)')
param gpuEnabled bool = false

@description('Minimum replica count')
param minReplicas int = 1

@description('Maximum replica count')
param maxReplicas int = 3

resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: environmentName
  location: location
  properties: {
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

resource backendApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'realty-backend'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
      }
      registries: [
        {
          server: acrLoginServer
          username: acrUsername
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: acrPassword
        }
        {
          name: 'database-url'
          value: databaseUrl
        }
      ]
    }
    template: {
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
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
              value: 'http://localhost:11434'
            }
          ]
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
        }
        {
          name: 'ollama'
          image: 'ollama/ollama:latest'
          resources: {
            // GPU-ready: bump cpu/memory and swap workload profile post-MVP
            cpu: json(gpuEnabled ? '4.0' : '2.0')
            memory: gpuEnabled ? '16Gi' : '4Gi'
          }
          volumeMounts: [
            {
              volumeName: 'ollama-data'
              mountPath: '/root/.ollama'
            }
          ]
        }
      ]
      volumes: [
        {
          name: 'ollama-data'
          storageType: 'EmptyDir'
        }
      ]
    }
  }
}

output backendUrl string = 'https://${backendApp.properties.configuration.ingress.fqdn}'
output backendIdentityPrincipalId string = backendApp.identity.principalId
