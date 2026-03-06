@description('The location for all resources. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('The API token needed to authenticate with the PageIndex wrapper API.')
@secure()
param apiToken string

@description('The OpenAI API key needed for the PageIndex core logic.')
@secure()
param openaiApiKey string

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

// 3. Container App (FastAPI Wrapper)
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
          name: 'openai-api-key'
          value: openaiApiKey
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
              name: 'OPENAI_API_KEY'
              secretRef: 'openai-api-key'
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
