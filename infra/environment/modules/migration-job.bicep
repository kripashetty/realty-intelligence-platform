@description('Name of the database migration Container Apps Job')
param jobName string

@description('Resource ID of the existing Container Apps environment')
param containerAppsEnvironmentId string

@description('Azure region')
param location string = resourceGroup().location

@description('Backend image containing Alembic and migration files')
param backendImage string

@description('Azure Container Registry login server')
param acrLoginServer string

@description('Resource ID of the user-assigned managed identity')
param workloadIdentityResourceId string

@description('Versionless Key Vault URI for the database URL secret')
param databaseUrlSecretUri string

@description('Maximum execution duration in seconds')
@minValue(60)
param replicaTimeout int = 1800

@description('Number of retries after a failed execution')
@minValue(0)
param replicaRetryLimit int = 1

@description('Tags applied to the migration job')
param tags object = {}

resource migrationJob 'Microsoft.App/jobs@2026-01-01' = {
  name: jobName
  location: location
  tags: tags

  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${workloadIdentityResourceId}': {}
    }
  }

  properties: {
    environmentId: containerAppsEnvironmentId
    workloadProfileName: 'Consumption'

    configuration: {
      triggerType: 'Manual'

      replicaTimeout: replicaTimeout
      replicaRetryLimit: replicaRetryLimit

      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
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
      containers: [
        {
          name: 'migration'
          image: backendImage

          // This assumes uv is installed in the backend image and
          // the working directory/image entrypoint can locate Alembic.
          command: [
            '/bin/sh'
            '-c'
          ]

          args: [

                  '''

                  set -eux

                  cd /app

                  test -n "$DATABASE_URL"

                  python -m alembic upgrade head

                  echo "Migration completed successfully."

                  '''

                ]

          env: [
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
          ]

          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
    }
  }
}

output jobId string = migrationJob.id
output jobName string = migrationJob.name
