targetScope = 'subscription'

param location string

param sharedResourceGroupName string
param environmentResourceGroupName string

param tags object = {}

resource sharedResourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: sharedResourceGroupName
  location: location
  tags: union(tags, {
    scope: 'shared'
  })
}

resource environmentResourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: environmentResourceGroupName
  location: location
  tags: union(tags, {
    scope: 'environment'
  })
}

output sharedResourceGroupName string = sharedResourceGroup.name
output environmentResourceGroupName string = environmentResourceGroup.name
