# CCF Push Connectors Reference (Public Preview — Feb 2026)

Source: https://learn.microsoft.com/en-us/azure/sentinel/create-push-codeless-connector

## Overview
Push connectors let your application send security events directly to Sentinel in real-time via the Azure Monitor Logs Ingestion API, rather than Sentinel polling your API.

**Status:** Public Preview (announced February 12, 2026)

## Push vs Pull

| Aspect | Pull (RestApiPoller) | Push |
|--------|---------------------|------|
| Who initiates | Sentinel polls your API | Your app sends to Sentinel |
| Latency | Polling interval (1-15+ min) | Near real-time |
| API endpoint needed | Yes — your API must be accessible | No — you POST to Azure |
| Data flow control | Sentinel-managed | App-controlled |
| Authentication | Various (Basic, APIKey, OAuth2, JWT) | Entra app OAuth 2.0 client_credentials |
| Resource creation | Manual ARM template | Automated on "Deploy" click |

## Prerequisites
- **Entra ID:** Permission to create app registrations (Application Developer role+)
- **Entra ID:** Permission to create app secrets
- **Azure RBAC:** Permission to assign Monitoring Metrics Publisher role on DCR (Owner or User Access Administrator)
- Publisher must be able to retrieve tokens from the Entra app

## What "Deploy" Creates Automatically
1. Microsoft Entra application with client secret
2. Data Collection Rule (DCR)
3. Data Collection Endpoint (DCE)
4. Custom log table
5. Role assignments (Monitoring Metrics Publisher on DCR)

## Connection Details Provided After Deploy
- Tenant ID
- Application (Client) ID
- Client Secret
- DCE URI (endpoint URL)
- DCR Immutable ID
- Stream Name

## Data Connector Configuration (kind: "Push")
```json
{
    "name": "MyPushConnector",
    "apiVersion": "2024-09-01",
    "type": "Microsoft.SecurityInsights/dataConnectors",
    "kind": "Push",
    "properties": {
        "connectorDefinitionName": "MyPushConnectorDefinition",
        "dcrConfig": {
            "streamName": "Custom-MyStream",
            "dataCollectionEndpoint": "[[parameters('dcrConfig').dataCollectionEndpoint]",
            "dataCollectionRuleImmutableId": "[[parameters('dcrConfig').dataCollectionRuleImmutableId]"
        },
        "auth": {
            "type": "Push",
            "AppId": "[[parameters('auth').appId]",
            "ServicePrincipalId": "[[parameters('auth').servicePrincipalId]"
        },
        "request": {
            "RetryCount": 1
        },
        "response": {
            "eventsJsonPaths": ["$"]
        }
    }
}
```

## Connector UI Definition Differences

### Connectivity Criteria — use IsConnectedQuery (not HasDataConnectors)
```json
"connectivityCriteria": [{
    "type": "IsConnectedQuery",
    "value": [
        "MyTable_CL\n| summarize LastLogReceived = max(TimeGenerated)\n| project IsConnected = LastLogReceived > ago(7d)"
    ]
}]
```

### Deploy Button — DeployPushConnectorButton
```json
{
    "type": "DeployPushConnectorButton",
    "parameters": {
        "label": "Deploy My Push connector resources",
        "applicationDisplayName": "My Push Connector Application"
    }
}
```

### CopyableLabel with fillWith for Auto-Populated Values
```json
{ "type": "CopyableLabel", "parameters": { "label": "Tenant ID", "fillWith": ["TenantId"] } },
{ "type": "CopyableLabel", "parameters": { "label": "Application ID", "fillWith": ["ApplicationId"], "placeholder": "Deploy first" } },
{ "type": "CopyableLabel", "parameters": { "label": "Client Secret", "fillWith": ["ApplicationSecret"], "placeholder": "Deploy first" } },
{ "type": "CopyableLabel", "parameters": { "label": "DCE URI", "fillWith": ["DataCollectionEndpoint"], "placeholder": "Deploy first" } },
{ "type": "CopyableLabel", "parameters": { "label": "DCR Immutable ID", "fillWith": ["DataCollectionRuleId"], "placeholder": "Deploy first" } },
{ "type": "CopyableLabel", "parameters": { "label": "Stream Name", "value": "Custom-MyStream" } }
```

Fixed values (like stream name) use `value`; auto-populated values use `fillWith`.

Supported `fillWith` values: `TenantId`, `ApplicationId`, `ApplicationSecret`, `DataCollectionEndpoint`, `DataCollectionRuleId`, `WorkspaceId`, `PrimaryKey`, `workspaceName`, `MicrosoftAwsAccount`, `subscriptionId`

## DCR for Push Connectors
Same structure as pull, but:
- Stream declarations should match what your app sends (not what the API returns)
- `transformKql` can add `TimeGenerated = now()` if your app doesn't send it

## Packaging for Content Hub
Push connectors use the Azure-Sentinel GitHub repository packaging tools:
1. Clone Azure-Sentinel repo
2. Create solution folder structure under `Solutions/`
3. Create: `table.json`, `DCR.json`, `connectorDefinition.json`, `dataConnector.json`
4. Create metadata: `Solution_*.json`, `SolutionMetadata.json`, `ReleaseNotes.md`
5. Run `createSolutionV3.ps1` packaging script
6. Deploy `Package/mainTemplate.json`

arm-ttk validation failures are **expected and normal** for CCF Push connectors.

## Client Code Pattern (Python)
```python
import requests
from datetime import datetime, timezone

# 1. Get OAuth token
token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
token_data = {
    "client_id": app_id,
    "scope": "https://monitor.azure.com//.default",
    "client_secret": app_secret,
    "grant_type": "client_credentials"
}
token = requests.post(token_url, data=token_data).json()["access_token"]

# 2. POST events to DCE
events = [{"TimeGenerated": datetime.now(timezone.utc).isoformat(), "EventType": "Alert", ...}]
url = f"{dce_uri}/dataCollectionRules/{dcr_id}/streams/{stream_name}?api-version=2023-01-01"
requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=events)
```

## Early Adopter Partners
- Keeper Security — password/secrets management telemetry
- Obsidian — SaaS application threat feeds
- Varonis — file activity and threat alerts
