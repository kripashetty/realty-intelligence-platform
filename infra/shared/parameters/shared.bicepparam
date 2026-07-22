using '../main.bicep'

param location = 'northeurope'

param acrName = 'realtydevacr'

param acrSku = 'Basic'

param tags = {
  application: 'realty'
  scope: 'shared'
  environment: 'shared'
  managedBy: 'bicep'
}
