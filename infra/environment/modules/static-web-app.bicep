@description('Static Web App resource name')
param staticWebAppName string

@description('Azure region supported by Static Web Apps')
param location string

@description('Static Web Apps SKU')
@allowed([
  'Free'
  'Standard'
])
param skuName string = 'Free'

@description('Tags applied to the Static Web App')
param tags object = {}

resource staticWebApp 'Microsoft.Web/staticSites@2023-12-01' = {
  name: staticWebAppName
  location: location
  tags: tags

  sku: {
    name: skuName
    tier: skuName
  }

  properties: {
    allowConfigFileUpdates: true
  }
}

output staticWebAppId string = staticWebApp.id
output staticWebAppName string = staticWebApp.name
output defaultHostname string = staticWebApp.properties.defaultHostname
output frontendUrl string = 'https://${staticWebApp.properties.defaultHostname}'
