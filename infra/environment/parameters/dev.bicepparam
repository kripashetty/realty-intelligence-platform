using '../main.bicep'

param environment = 'dev'
param location = 'northeurope'
param frontendLocation = 'westeurope'

param postgresAdminLogin = 'realtyadmin'
param postgresAdminPassword =readEnvironmentVariable('POSTGRES_ADMIN_PASSWORD')

param backendImage = readEnvironmentVariable('BACKEND_IMAGE')


param acrName = 'realtydevacr'

param acrResourceGroupName = 'realty-shared-rg'

param tags = {

  application: 'realty'

  environment: 'dev'

  managedBy: 'bicep'

  workload: 'portfolio'

}

param ollamaImage = 'ollama/ollama:0.6.8'
// param ollamaModel = 'llama3.1:8b'
param ollamaModel = 'qwen2.5:0.5b'


// using '../main.bicep'

// param environment = 'dev'
// param location = 'northeurope'

// param applicationName = 'realty'

// param acrName = 'realtydevacr'
// param acrResourceGroupName = 'realty-shared-rg'

// param postgresDatabaseName = 'realty'
// param postgresAdminUsername = 'realtyadmin'
// param postgresSkuName = 'Standard_B1ms'

// param backendMinReplicas = 0
// param backendMaxReplicas = 2

// param ollamaImage = 'ollama/ollama:<tested-version>'
// param ollamaModel = 'llama3.1:8b'

// param tags = {
//   application: 'realty'
//   environment: 'dev'
//   managedBy: 'bicep'
// }
