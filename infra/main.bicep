@description('The location for all resources. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('The API token needed to authenticate with the PageIndex wrapper API.')
@secure()
param apiToken string

@description('The Docker image to deploy.')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('The login server of the shared ACR (e.g. asireonclawacr.azurecr.io).')
param acrLoginServer string

@description('The admin password for the shared ACR.')
@secure()
param acrPassword string

// Variables to enforce unique, valid names
var logAnalyticsWorkspaceName = 'law-pageindex-${uniqueString(resourceGroup().id)}'
var containerAppEnvironmentName = 'cae-pageindex-${uniqueString(resourceGroup().id)}'
var containerAppName = 'ca-pageindex-api'
var openAiAccountName = 'pageindex-openai-${uniqueString(resourceGroup().id)}'

// 1. Log Analytics Workspace (for Container App logs)
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  tags: {
    Component: 'PageIndex'
  }
  properties: {
    sku: {
      name: 'PerGB2018'
    }
  }
}

// 2. Container Apps Environment
resource containerAppEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerAppEnvironmentName
  location: location
  tags: {
    Component: 'PageIndex'
  }
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}
// 3. Azure OpenAI (for LLM-powered document structure extraction)
resource openAiAccount 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: openAiAccountName
  location: location
  tags: {
    Component: 'PageIndex'
  }
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openAiAccountName
    publicNetworkAccess: 'Enabled'
  }
}

resource gpt4oMiniDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openAiAccount
  name: 'gpt-4o-mini'
  sku: {
    name: 'Standard'
    capacity: 1000 // 1M tokens per minute
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o-mini'
      version: '2024-07-18'
    }
  }
}

// 4. Container App (FastAPI Wrapper)
resource apiContainerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  tags: {
    Component: 'PageIndex'
  }
  properties: {
    managedEnvironmentId: containerAppEnvironment.id
    configuration: {
      ingress: {
        external: true // Exposed externally — secured by X-API-Key authentication
        targetPort: 8000
        allowInsecure: false

        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          server: acrLoginServer
          username: split(acrLoginServer, '.')[0]
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: acrPassword
        }
        {
          name: 'api-token'
          value: apiToken
        }
        {
          name: 'azure-openai-key'
          value: openAiAccount.listKeys().key1
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'pageindex-api'
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
          env: [
            {
              name: 'API_TOKEN'
              secretRef: 'api-token'
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: openAiAccount.properties.endpoint
            }
            {
              name: 'AZURE_OPENAI_KEY'
              secretRef: 'azure-openai-key'
            }
            {
              name: 'AZURE_OPENAI_DEPLOYMENT'
              value: gpt4oMiniDeployment.name
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1 // Keep warm to avoid cold-start timeouts on large PDFs
        maxReplicas: 2
      }
    }
  }
}

// Outputs
output apiUrl string = apiContainerApp.properties.configuration.ingress.fqdn
output openAiEndpoint string = openAiAccount.properties.endpoint
