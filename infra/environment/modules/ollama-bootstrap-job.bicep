@description('Name of the Ollama model bootstrap job')
param jobName string

@description('Resource ID of the existing Container Apps environment')
param containerAppsEnvironmentId string

@description('Azure region')
param location string = resourceGroup().location

@description('Internal Ollama base URL')
param ollamaUrl string

@description('Ollama model name and tag to install')
param ollamaModel string

@description('Pinned curl container image')
param curlImage string = 'curlimages/curl:8.14.1'

@description('Maximum execution duration in seconds')
@minValue(60)
param replicaTimeout int = 7200

@description('Number of retries after a failed execution')
@minValue(0)
param replicaRetryLimit int = 0

@description('Tags applied to the bootstrap job')
param tags object = {}

resource bootstrapJob 'Microsoft.App/jobs@2026-01-01' = {
  name: jobName
  location: location
  tags: tags

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
    }

    template: {
      containers: [
        {
          name: 'model-bootstrap'
          image: curlImage

          command: [
            '/bin/sh'
            '-c'
          ]

          args: [
            '''
            set -eux

            OLLAMA_URL="$1"
            OLLAMA_MODEL="$2"

            echo "Waiting for Ollama at $OLLAMA_URL..."

            attempt=1
            while [ "$attempt" -le 60 ]; do
              if curl \
                --connect-timeout 10 \
                --max-time 20 \
                --fail \
                --silent \
                --show-error \
                "$OLLAMA_URL/api/tags" > /dev/null; then
                echo "Ollama is ready."
                break
              fi

              if [ "$attempt" -eq 60 ]; then
                echo "Ollama did not become ready in time."
                exit 20
              fi

              attempt=$((attempt + 1))
              sleep 5
            done

            echo "Pulling model $OLLAMA_MODEL..."

            curl \
              --connect-timeout 15 \
              --max-time 6900 \
              --fail-with-body \
              --show-error \
              --no-buffer \
              --request POST \
              --header "Content-Type: application/json" \
              --data "{\"model\":\"$OLLAMA_MODEL\",\"stream\":true}" \
              "$OLLAMA_URL/api/pull"

            echo
            echo "Pull request completed."
            echo "Verifying model $OLLAMA_MODEL..."

            TAGS="$(
              curl \
                --connect-timeout 10 \
                --max-time 30 \
                --fail-with-body \
                --silent \
                --show-error \
                "$OLLAMA_URL/api/tags"
            )"

            printf '%s\n' "$TAGS"

            if printf '%s\n' "$TAGS" | grep -F "$OLLAMA_MODEL" > /dev/null; then
              echo "Model verified."
            else
              echo "WARNING: pull returned successfully, but model was not found in /api/tags."
              exit 30
            fi

            echo "Model bootstrap completed successfully."
            '''
            'bootstrap'
            ollamaUrl
            ollamaModel
          ]

          env: [
            {
              name: 'OLLAMA_URL'
              value: ollamaUrl
            }
            {
              name: 'OLLAMA_MODEL'
              value: ollamaModel
            }
          ]

          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
    }
  }
}

output jobId string = bootstrapJob.id
output jobName string = bootstrapJob.name
