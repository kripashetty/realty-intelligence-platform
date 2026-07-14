using '../main.bicep'

param environment = 'prod'
param location = 'germanywestcentral'
param postgresAdminLogin = 'realtyadmin'
// postgresAdminPassword — supply via az deployment group create --parameters postgresAdminPassword=<secret>
// or via a Key Vault reference in CI/CD
// backendImage — supply at deploy time: myacr.azurecr.io/realty-backend:<tag>
param acrLoginServer = ''
param acrUsername = ''
// acrPassword — supply at deploy time
