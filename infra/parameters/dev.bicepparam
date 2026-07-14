using '../main.bicep'

param environment = 'dev'
param location = 'germanywestcentral'
param postgresAdminLogin = 'realtyadmin'
// postgresAdminPassword — supply via az deployment group create --parameters postgresAdminPassword=<secret>
// or via a Key Vault reference in CI/CD
param backendImage = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param acrLoginServer = ''
param acrUsername = ''
// acrPassword — supply at deploy time
