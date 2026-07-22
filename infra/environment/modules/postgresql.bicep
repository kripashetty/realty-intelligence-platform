@description('Name of the PostgreSQL Flexible Server')
param serverName string

@description('Name of the application database')
param databaseName string = 'realty'

@description('PostgreSQL administrator login name')
param administratorLogin string

@description('PostgreSQL administrator password used during provisioning')
@secure()
param administratorLoginPassword string

@description('Azure region')
param location string = resourceGroup().location

@description('PostgreSQL compute SKU')
param skuName string = 'Standard_B1ms'

@description('PostgreSQL compute tier')
@allowed([
  'Burstable'
  'GeneralPurpose'
  'MemoryOptimized'
])
param skuTier string = 'Burstable'

@description('Storage size in GB')
@minValue(32)
param storageSizeGB int = 32

@description('Backup retention period in days')
@minValue(7)
@maxValue(35)
param backupRetentionDays int = 7

@description('Whether PostgreSQL has a public network endpoint')
@allowed([
  'Enabled'
  'Disabled'
])
param publicNetworkAccess string = 'Enabled'

@description('Tags applied to PostgreSQL resources')
param tags object = {}

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2025-08-01' = {
  name: serverName
  location: location
  tags: tags

  sku: {
    name: skuName
    tier: skuTier
  }

  properties: {
    version: '15'

    administratorLogin: administratorLogin
    administratorLoginPassword: administratorLoginPassword

    authConfig: {
      activeDirectoryAuth: 'Disabled'
      passwordAuth: 'Enabled'
    }

    network: {
      publicNetworkAccess: publicNetworkAccess
    }

    storage: {
      storageSizeGB: storageSizeGB
      autoGrow: 'Enabled'
    }

    backup: {
      backupRetentionDays: backupRetentionDays
      geoRedundantBackup: 'Disabled'
    }

    highAvailability: {
      mode: 'Disabled'
    }
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2025-08-01' = {
  parent: postgresServer
  name: databaseName

  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

output serverId string = postgresServer.id
output serverName string = postgresServer.name
output serverFqdn string = postgresServer.properties.fullyQualifiedDomainName
output databaseName string = database.name
