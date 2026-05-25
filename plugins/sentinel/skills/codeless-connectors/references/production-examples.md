# Production Connector Examples

Annotated excerpts from production CCF connectors in the [Azure-Sentinel](https://github.com/Azure/Azure-Sentinel) repository. Use as copy-paste starting points and to understand real-world patterns.

All examples use the **separate-file format** from `Solutions/` (see `reference/troubleshooting.md` for format details). `{{placeholder}}` values are resolved at connect-time by the CCF platform.

---

## 1. Cisco Meraki — Multi-connection + LinkHeader + ASIM Multi-table

**Source:** `Solutions/Cisco Meraki Events via REST API/Data Connectors/CiscoMerakiMultiRule_ccp/`

**Why notable:** Three connections in one connector, each targeting a different ASIM table. Demonstrates `linkHeaderRelLinkName`, `User-Agent: Scuba-Microsoft`, and multi-stream DCR with ASIM transforms.

### PollingConfig (3 connections)

```json
[
    {
        "name": "CiscoMerakiAPIRequest",
        "kind": "RestApiPoller",
        "properties": {
            "connectorDefinitionName": "CiscoMerakiMultiRule",
            "dataType": "ASimWebSessionLogs",
            "dcrConfig": {
                "streamName": "Custom-CiscoMeraki_API",
                "dataCollectionEndpoint": "{{dataCollectionEndpoint}}",
                "dataCollectionRuleImmutableId": "{{dataCollectionRuleImmutableId}}"
            },
            "auth": {
                "type": "APIKey",
                "ApiKey": "{{apiKey}}",
                "ApiKeyName": "X-Cisco-Meraki-API-Key"
            },
            "request": {
                "apiEndpoint": "https://api.meraki.com/api/v1/organizations/{{organization}}/apiRequests",
                "httpMethod": "GET",
                "queryParameters": { "perPage": 1000 },
                "queryWindowInMin": 5,
                "queryTimeFormat": "UnixTimestamp",
                "StartTimeAttributeName": "t0",
                "EndTimeAttributeName": "t1",
                "rateLimitQPS": 2,
                "retryCount": 3,
                "timeoutInSeconds": 60,
                "headers": {
                    "Accept": "application/json",
                    "User-Agent": "Scuba-Microsoft"
                }
            },
            "paging": {
                "pagingType": "LinkHeader",
                "linkHeaderRelLinkName": "rel=next"      // <-- follows the "next" rel link
            },
            "response": { "eventsJsonPaths": ["$"] }
        }
    },
    {
        "name": "CiscoMerakiConfigRequest",
        "kind": "RestApiPoller",
        "properties": {
            "connectorDefinitionName": "CiscoMerakiMultiRule",
            "dataType": "ASimAuditEventLogs",
            "dcrConfig": {
                "streamName": "Custom-CiscoMeraki_Configuration",
                "dataCollectionEndpoint": "{{dataCollectionEndpoint}}",
                "dataCollectionRuleImmutableId": "{{dataCollectionRuleImmutableId}}"
            },
            "auth": {
                "type": "APIKey",
                "ApiKey": "{{apiKey}}",
                "ApiKeyName": "X-Cisco-Meraki-API-Key"
            },
            "request": {
                "apiEndpoint": "https://api.meraki.com/api/v1/organizations/{{organization}}/configurationChanges",
                "httpMethod": "GET",
                "queryParameters": { "perPage": 1000 },
                "queryWindowInMin": 5,
                "queryTimeFormat": "UnixTimestamp",
                "StartTimeAttributeName": "t0",
                "EndTimeAttributeName": "t1",
                "rateLimitQPS": 2,
                "retryCount": 3,
                "timeoutInSeconds": 60,
                "headers": {
                    "Accept": "application/json",
                    "User-Agent": "Scuba-Microsoft"
                }
            },
            "paging": {
                "pagingType": "LinkHeader",
                "linkHeaderRelLinkName": "rel=prev"       // <-- follows "prev" (reverse-chronological API)
            },
            "response": { "eventsJsonPaths": ["$"] }
        }
    },
    {
        "name": "CiscoMerakiIDSRequest",
        "kind": "RestApiPoller",
        "properties": {
            "connectorDefinitionName": "CiscoMerakiMultiRule",
            "dataType": "ASimNetworkSessionLogs",
            "dcrConfig": {
                "streamName": "Custom-CiscoMeraki_IDS",
                "dataCollectionEndpoint": "{{dataCollectionEndpoint}}",
                "dataCollectionRuleImmutableId": "{{dataCollectionRuleImmutableId}}"
            },
            "auth": {
                "type": "APIKey",
                "ApiKey": "{{apiKey}}",
                "ApiKeyName": "X-Cisco-Meraki-API-Key"
            },
            "request": {
                "apiEndpoint": "https://api.meraki.com/api/v1/organizations/{{organization}}/appliance/security/events",
                "httpMethod": "GET",
                "queryParameters": { "perPage": 1000 },
                "queryWindowInMin": 5,
                "queryTimeFormat": "UnixTimestamp",
                "StartTimeAttributeName": "t0",
                "EndTimeAttributeName": "t1",
                "rateLimitQPS": 2,
                "retryCount": 3,
                "timeoutInSeconds": 60,
                "headers": {
                    "Accept": "application/json",
                    "User-Agent": "Scuba-Microsoft"
                }
            },
            "paging": {
                "pagingType": "LinkHeader",
                "linkHeaderRelLinkName": "rel=next"
            },
            "response": { "eventsJsonPaths": ["$"] }
        }
    }
]
```

### DCR (3 streams, 3 ASIM destination tables)

```json
{
    "name": "CiscoMerakiMultiRules",
    "type": "Microsoft.Insights/dataCollectionRules",
    "properties": {
        "dataCollectionEndpointId": "{{dataCollectionEndpointId}}",
        "streamDeclarations": {
            "Custom-CiscoMeraki_API": {
                "columns": [
                    { "name": "ts", "type": "datetime" },
                    { "name": "adminId", "type": "string" },
                    { "name": "host", "type": "string" },
                    { "name": "method", "type": "string" },
                    { "name": "path", "type": "string" },
                    { "name": "queryString", "type": "string" },
                    { "name": "userAgent", "type": "string" },
                    { "name": "responseCode", "type": "int" },
                    { "name": "sourceIp", "type": "string" },
                    { "name": "version", "type": "int" },
                    { "name": "operationId", "type": "string" }
                ]
            },
            "Custom-CiscoMeraki_Configuration": {
                "columns": [
                    { "name": "ts", "type": "datetime" },
                    { "name": "adminName", "type": "string" },
                    { "name": "adminEmail", "type": "string" },
                    { "name": "adminId", "type": "string" },
                    { "name": "networkName", "type": "string" },
                    { "name": "networkId", "type": "string" },
                    { "name": "ssidName", "type": "string" },
                    { "name": "ssidNumber", "type": "string" },
                    { "name": "page", "type": "string" },
                    { "name": "label", "type": "string" },
                    { "name": "oldValue", "type": "string" },
                    { "name": "newValue", "type": "string" }
                ]
            },
            "Custom-CiscoMeraki_IDS": {
                "columns": [
                    { "name": "ts", "type": "datetime" },
                    { "name": "eventType", "type": "string" },
                    { "name": "deviceMac", "type": "string" },
                    { "name": "clientMac", "type": "string" },
                    { "name": "srcIp", "type": "string" },
                    { "name": "destIp", "type": "string" },
                    { "name": "protocol", "type": "string" },
                    { "name": "priority", "type": "string" },
                    { "name": "classification", "type": "string" },
                    { "name": "blocked", "type": "boolean" },
                    { "name": "message", "type": "string" },
                    { "name": "signature", "type": "string" },
                    { "name": "ruleId", "type": "string" }
                ]
            }
        },
        "destinations": {
            "logAnalytics": [{
                "workspaceResourceId": "{{workspaceResourceId}}",
                "name": "clv2ws1"
            }]
        },
        "dataFlows": [
            {
                "streams": ["Custom-CiscoMeraki_API"],
                "destinations": ["clv2ws1"],
                "transformKql": "source | extend TimeGenerated = ts, EventCount = toint(1), EventResult = case(responseCode >= 200 and responseCode <= 299, \"Success\", \"Failure\"), EventProduct = \"Meraki\", EventVendor = \"Cisco\", EventType = \"HTTPsession\", EventSchemaVersion = \"0.2.5\", Url = strcat(host,path,'?',queryString), HttpRequestMethod = method, HttpStatusCode = tostring(responseCode), SrcIpAddr = sourceIp, EventStartTime = ts, EventEndTime = ts, Dvc = \"Meraki\"",
                "outputStream": "Microsoft-ASimWebSessionLogs"       // <-- Microsoft- prefix for ASIM
            },
            {
                "streams": ["Custom-CiscoMeraki_Configuration"],
                "destinations": ["clv2ws1"],
                "transformKql": "source | project-rename TimeGenerated = ts, OldValue = oldValue, NewValue = newValue, ActorUsername = adminEmail, ActorUserId = adminId | extend EventSchemaVersion = \"0.1\", EventCount = toint(1), EventResult = \"Success\", EventProduct = \"Meraki\", EventVendor = \"Cisco\", Operation = strcat(page,'/',label), Object = networkName, ObjectType = \"Other\", EventType = case(isempty(OldValue),\"Create\", isempty(NewValue),\"Delete\", \"Set\"), EventStartTime = TimeGenerated, EventEndTime = TimeGenerated",
                "outputStream": "Microsoft-ASimAuditEventLogs"
            },
            {
                "streams": ["Custom-CiscoMeraki_IDS"],
                "destinations": ["clv2ws1"],
                "transformKql": "source | where eventType == \"IDS Alert\" | extend srcIpSplit = split(srcIp,':'), dstIpSplit = split(destIp,':') | project-rename TimeGenerated = ts, EventOriginalType = eventType, DvcMacAddr = deviceMac, SrcMacAddr = clientMac, EventOriginalSeverity = priority, EventMessage = message, NetworkRuleName = ruleId | extend EventCount = toint(1), EventResult = iif(blocked,\"Failure\",\"Success\"), EventProduct = \"Meraki\", EventVendor = \"Cisco\", EventType = \"Notable\", SrcIpAddr = tostring(srcIpSplit[0]), DstIpAddr = tostring(dstIpSplit[0]), Dvc = DvcMacAddr, EventStartTime = TimeGenerated, EventEndTime = TimeGenerated",
                "outputStream": "Microsoft-ASimNetworkSessionLogs"
            }
        ]
    }
}
```

### Connector Definition (multi-table UI)

```json
{
    "kind": "Customizable",
    "properties": {
        "connectorUiConfig": {
            "id": "CiscoMerakiMultiRule",
            "title": "Cisco Meraki (using REST API)",
            "publisher": "Microsoft",
            "graphQueriesTableName": "ASimNetworkSessionLogs",
            "graphQueries": [
                {
                    "metricName": "Total IDS alerts received",
                    "legend": "Get IDS Alerts",
                    "baseQuery": "{{graphQueriesTableName}} | where EventProduct == \"Meraki\" and EventVendor == \"Cisco\""
                },
                {
                    "metricName": "Total API request events received",
                    "legend": "Get API Request",
                    "baseQuery": "ASimWebSessionLogs | where EventProduct == \"Meraki\" and EventVendor == \"Cisco\" and EventOriginalType == \"API Request\""
                },
                {
                    "metricName": "Total Configuration Changes received",
                    "legend": "Get Configuration Changes",
                    "baseQuery": "ASimAuditEventLogs | where EventProduct == \"Meraki\" and EventVendor == \"Cisco\""
                }
            ],
            "dataTypes": [
                {
                    "name": "{{graphQueriesTableName}}",
                    "lastDataReceivedQuery": "{{graphQueriesTableName}}\n| where TimeGenerated > ago(7d)\n| where EventProduct == \"Meraki\" and EventVendor == \"Cisco\"\n| summarize Time = max(TimeGenerated)\n| where isnotempty(Time)"
                },
                {
                    "name": "ASimWebSessionLogs",
                    "lastDataReceivedQuery": "ASimWebSessionLogs\n| where TimeGenerated > ago(7d)\n| where EventProduct == \"Meraki\" and EventVendor == \"Cisco\"\n| summarize Time = max(TimeGenerated)\n| where isnotempty(Time)"
                },
                {
                    "name": "ASimAuditEventLogs",
                    "lastDataReceivedQuery": "ASimAuditEventLogs\n| where TimeGenerated > ago(7d)\n| where EventProduct == \"Meraki\" and EventVendor == \"Cisco\"\n| summarize Time = max(TimeGenerated)\n| where isnotempty(Time)"
                }
            ],
            "connectivityCriteria": [{ "type": "HasDataConnectors" }],
            "instructionSteps": [{
                "instructions": [
                    { "type": "Textbox", "parameters": { "label": "Organization Id", "type": "text", "name": "organization" } },
                    { "type": "Textbox", "parameters": { "label": "API Key", "type": "password", "name": "apiKey" } },
                    { "type": "ConnectionToggleButton", "parameters": { "label": "toggle", "name": "toggle" } }
                ]
            }]
        }
    }
}
```

---

## 2. 1Password — Multi-endpoint POST + NextPageToken + Shared Stream

**Source:** `Solutions/1Password/Data Connectors/1Password_ccpv2/`

**Why notable:** Three endpoints (sign-in attempts, audit events, item usages) all share the same `Custom-OnePasswordEventLogs_CL` stream. Uses POST with `queryParametersTemplate` for time windowing. DCR uses `case()` to detect log source type.

### PollingConfig (one of three connections — others identical except endpoint)

```json
{
    "name": "OnePasswordSignInEvents",
    "kind": "RestApiPoller",
    "properties": {
        "connectorDefinitionName": "1PasswordCCPDefinition",
        "dataType": "OnePasswordEventLogs_CL",
        "dcrConfig": {
            "streamName": "Custom-OnePasswordEventLogs_CL",          // <-- shared across all 3 connections
            "dataCollectionEndpoint": "{{dataCollectionEndpoint}}",
            "dataCollectionRuleImmutableId": "{{dataCollectionRuleImmutableId}}"
        },
        "auth": {
            "type": "APIKey",
            "ApiKey": "{{ApiToken}}",
            "ApiKeyName": "Authorization",
            "ApiKeyIdentifier": "Bearer"                              // <-- prepends "Bearer " to the key
        },
        "request": {
            "apiEndpoint": "{{BaseUrl}}/api/v1/signinattempts",
            "httpMethod": "Post",
            "queryWindowInMin": 5,
            "queryTimeFormat": "yyyy-MM-ddTHH:mm:ssZ",
            "rateLimitQPS": 1,
            "retryCount": 3,
            "timeoutInSeconds": 60,
            "headers": { "Content-Type": "application/json" },
            "queryParametersTemplate": "{\"limit\": 1000, \"start_time\": \"{_QueryWindowStartTime}\", \"end_time\": \"{_QueryWindowEndTime}\" }",
            "isPostPayloadJson": true                                 // <-- POST body is JSON
        },
        "response": {
            "format": "json",
            "eventsJsonPaths": ["$.items"]
        },
        "paging": {
            "pagingType": "NextPageToken",
            "NextPageParaName": "cursor",
            "nextPageTokenJsonPath": "$.cursor",
            "hasNextFlagJsonPath": "$.has_more"                       // <-- stops paging when false
        }
    }
}
```

### DCR (single stream, log source detection via KQL)

```json
{
    "properties": {
        "dataFlows": [{
            "streams": ["Custom-OnePasswordEventLogs_CL"],
            "destinations": ["clv2ws1"],
            "outputStream": "Custom-OnePasswordEventLogs_CL",
            "transformKql": "source | extend TimeGenerated = now(), log_source = case(isnotempty(used_version) or isnotempty(aux_id), 'itemusages', isnotempty(country), 'signinattempts', isempty(used_version) and isempty(aux_id) and isempty(country), 'auditevents', 'unknown')"
        }]
    }
}
```

---

## 3. Auth0 — OAuth2 client_credentials + PersistentToken

**Source:** `Solutions/Auth0/Data Connectors/Auth0_CCP/`

**Why notable:** OAuth2 `client_credentials` grant with dynamic `TokenEndpoint` constructed from a user-provided domain parameter. Uses `PersistentToken` pagination (the API remembers position server-side).

### PollingConfig

```json
{
    "name": "Auth0Logs",
    "kind": "RestApiPoller",
    "properties": {
        "connectorDefinitionName": "Auth0ConnectorCCPDefinition",
        "dataType": "Auth0Logs_CL",
        "auth": {
            "type": "OAuth2",
            "ClientId": "{{ClientId}}",
            "ClientSecret": "{{ClientSecret}}",
            "GrantType": "client_credentials",
            "TokenEndpoint": "[[concat(parameters('Domain'),'/oauth/token')]",        // <-- ARM expression
            "TokenEndpointQueryParameters": {
                "audience": "[[concat(parameters('Domain'),'/api/v2/')]"              // <-- extra token params
            }
        },
        "request": {
            "apiEndpoint": "[[concat(parameters('Domain'),'/api/v2/logs')]",
            "headers": { "Accept": "application/json" },
            "httpMethod": "Get"
        },
        "response": {
            "eventsJsonPaths": ["$"],
            "format": "json"
        },
        "dcrConfig": {
            "streamName": "Custom-Auth0Logs",
            "dataCollectionEndpoint": "{{dataCollectionEndpoint}}",
            "dataCollectionRuleImmutableId": "{{dataCollectionRuleImmutableId}}"
        },
        "paging": {
            "pagingType": "PersistentToken",
            "NextPageParaName": "from",                                               // <-- query param for cursor
            "nextPageTokenJsonPath": "$.[-1:].log_id",                                // <-- last item's log_id
            "pageSizeParameterName": "take",
            "pageSize": 100
        }
    }
}
```

---

## 4. Azure DevOps — OAuth2 authorization_code + NextPageToken

**Source:** `Solutions/AzureDevOpsAuditing/Data Connectors/AzureDevOpsAuditLogs_CCP/`

**Why notable:** OAuth2 `authorization_code` flow (user-interactive auth). Shows `RedirectUri`, `Scope`, `AuthorizationCode`, `AuthorizationEndpoint` fields. Uses both `StartTimeAttributeName`/`EndTimeAttributeName` AND explicit `queryParameters` with built-in variables.

### PollingConfig

```json
{
    "name": "Azure DevOps Audit Logs Polling Config",
    "kind": "RestApiPoller",
    "properties": {
        "connectorDefinitionName": "AzureDevOpsAuditLogs",
        "dataType": "ADOAuditLogs_CL",
        "dcrConfig": {
            "streamName": "Custom-ADOAuditLogs",
            "dataCollectionEndpoint": "{{dataCollectionEndpoint}}",
            "dataCollectionRuleImmutableId": "{{dataCollectionRuleImmutableId}}"
        },
        "auth": {
            "type": "OAuth2",
            "ClientSecret": "[[parameters('ClientSecret')]",
            "ClientId": "[[parameters('ClientId')]",
            "GrantType": "authorization_code",
            "AuthorizationCode": "[[parameters('AuthorizationCode')]",
            "RedirectUri": "{{redirectUri}}",
            "Scope": "499b84ac-1321-427f-aa17-267ca6975798/.default openid offline_access",
            "TokenEndpoint": "[[parameters('tokenEndpoint')]",
            "AuthorizationEndpoint": "[[parameters('authorizationEndpoint')]",
            "TokenEndpointHeaders": {
                "Content-Type": "application/x-www-form-urlencoded"
            }
        },
        "request": {
            "apiEndpoint": "[[parameters('apiEndpoint')]",
            "httpMethod": "GET",
            "queryWindowInMin": 5,
            "queryTimeFormat": "yyyy-MM-ddTHH:mm:ss.000000+00:00",      // <-- custom time format
            "rateLimitQPS": 1,
            "retryCount": 3,
            "timeoutInSeconds": 60,
            "StartTimeAttributeName": "startTime",
            "EndTimeAttributeName": "endTime",
            "headers": {
                "Accept": "application/json",
                "User-Agent": "Scuba"                                    // <-- Scuba header
            }
        },
        "response": {
            "eventsJsonPaths": ["$.decoratedAuditLogEntries"],
            "format": "json"
        },
        "paging": {
            "pagingType": "NextPageToken",
            "nextPageTokenJsonPath": "$.continuationToken",
            "NextPageParaName": "continuationToken",
            "hasNextFlagJsonPath": "$.hasMore"
        }
    }
}
```

---

## 5. Box — OAuth2 with Custom Token Parameters + startTime Only

**Source:** `Solutions/Box/Data Connectors/BoxEvents_ccp/`

**Why notable:** OAuth2 `client_credentials` with `TokenEndpointQueryParameters` for Box-specific `box_subject_type` and `box_subject_id`. Uses `StartTimeAttributeName` without `EndTimeAttributeName` (only a "since" filter). Note `rateLimitQPS` casing (capital QPS).

### PollingConfig

```json
{
    "name": "BoxEventsCCPPolling",
    "kind": "RestApiPoller",
    "properties": {
        "connectorDefinitionName": "BoxEventsCCPDefinition",
        "dataType": "BoxEventsV2_CL",
        "auth": {
            "type": "OAuth2",
            "ClientSecret": "{{clientSecret}}",
            "ClientId": "{{clientId}}",
            "GrantType": "client_credentials",
            "TokenEndpoint": "https://api.box.com/oauth2/token",
            "TokenEndpointHeaders": {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            "TokenEndpointQueryParameters": {                            // <-- Box-specific token params
                "box_subject_type": "enterprise",
                "box_subject_id": "{{boxEnterpriseId}}"
            }
        },
        "request": {
            "apiEndpoint": "https://api.box.com/2.0/events",
            "queryParameters": { "stream_type": "admin_logs" },
            "rateLimitQPS": 10,                                          // <-- schema's canonical casing
            "queryWindowInMin": 5,
            "httpMethod": "GET",
            "retryCount": 3,
            "timeoutInSeconds": 60,
            "queryTimeFormat": "yyyy-MM-ddTHH:mm:ssZ",
            "StartTimeAttributeName": "created_after",                   // <-- no EndTimeAttributeName
            "headers": { "Accept": "*/*" }
        },
        "response": {
            "eventsJsonPaths": ["$.entries"],
            "format": "json"
        },
        "paging": {
            "pagingType": "PersistentToken",
            "nextPageTokenJsonPath": "$.next_stream_position",
            "NextPageParaName": "stream_position"
        },
        "dcrConfig": {
            "dataCollectionEndpoint": "{{dataCollectionEndpoint}}",
            "dataCollectionRuleImmutableId": "{{dataCollectionRuleImmutableId}}",
            "streamName": "Custom-Box_CL"
        }
    }
}
```

---

## 6. Atlassian Jira — Basic Auth + Offset (v2 format)

**Source:** `Solutions/AtlassianJiraAudit/Data Connectors/JiraAuditAPISentinelConnector_ccpv2/`

**Why notable:** Simple Basic auth pattern. Offset pagination with `pageSizeParameterName` (canonical) and `offsetParaName`. Good starting template for simple connectors.

### PollingConfig

```json
{
    "name": "AtlassianJiraCCPPolling",
    "kind": "RestApiPoller",
    "properties": {
        "connectorDefinitionName": "JiraAuditCCPDefinition",
        "dataType": "Jira_Audit_v2_CL",
        "dcrConfig": {
            "dataCollectionEndpoint": "{{dataCollectionEndpoint}}",
            "dataCollectionRuleImmutableId": "{{dataCollectionRuleImmutableId}}",
            "streamName": "Custom-Jira_Audit_v2_CL"
        },
        "auth": {
            "type": "Basic",
            "UserName": "{{userid}}",
            "Password": "{{apikey}}"
        },
        "request": {
            "apiEndpoint": "https://{{jiraorganizationurl}}/rest/api/3/auditing/record",
            "httpMethod": "GET",
            "retryCount": 3,
            "timeoutInSeconds": 60,
            "queryTimeFormat": "yyyy-MM-ddTHH:mm:ssZ",
            "headers": {
                "Accept": "application/json",
                "User-Agent": "Scuba"
            },
            "StartTimeAttributeName": "from",
            "EndTimeAttributeName": "to"
        },
        "paging": {
            "pagingType": "Offset",
            "offsetParaName": "offset",
            "pageSizeParameterName": "limit",
            "pageSize": 1000
        },
        "response": {
            "eventsJsonPaths": ["$.records"],
            "format": "json"
        }
    }
}
```

### Legacy v1 (APIPolling) — same connector, old format

For comparison, the original Jira connector at `DataConnectors/AtlassianJiraAudit/` uses the v1 format:

```json
{
    "kind": "APIPolling",                                               // <-- v1 kind
    "type": "Microsoft.OperationalInsights/workspaces/providers/dataConnectors",
    "properties": {
        "connectorUiConfig": {                                          // <-- UI config inline
            "id": "AtlassianJira",
            "title": "Atlassian Jira",
            "connectivityCriteria": [{ "type": "SentinelKindsV2" }],   // <-- v1 connectivity type
            "instructionSteps": [{
                "instructions": [{
                    "type": "BasicAuth",                                // <-- v1 auth instruction type
                    "parameters": { "enable": "true" }
                }]
            }]
        },
        "pollingConfig": {                                              // <-- v1 config block
            "auth": { "authType": "Basic" },                           // <-- authType not type
            "request": {
                "apiEndpoint": "https://{{domain}}/rest/api/3/auditing/record",
                "httpMethod": "Get",
                "queryTimeFormat": "yyyy-MM-ddTHH:mm:ssZ",
                "startTimeAttributeName": "from",
                "endTimeAttributeName": "to",
                "queryWindowInMin": 5
            },
            "paging": {
                "pagingType": "Offset",
                "offsetParaName": "offset",
                "pageSizeParaName": "limit",
                "pageSize": 1000
            },
            "response": { "eventsJsonPaths": ["$..records"] }          // <-- deep scan ($..records)
        }
    }
}
```

---

## 7. Proofpoint TAP — Multiple eventsJsonPaths + Time Interval (Legacy v1)

**Source:** `DataConnectors/Proofpoint TAP/ProofpointTAPNativePollerConnector/`

**Why notable:** Uses `queryTimeIntervalAttributeName` to send a combined time interval. Multiple `eventsJsonPaths` entries collect data from different JSON branches in a single response. Legacy APIPolling format.

### PollingConfig (v1 format)

```json
{
    "kind": "APIPolling",
    "properties": {
        "pollingConfig": {
            "auth": { "authType": "Basic" },
            "request": {
                "apiEndpoint": "https://tap-api-v2.proofpoint.com/v2/siem/all",
                "httpMethod": "Get",
                "queryTimeIntervalAttributeName": "interval",            // <-- combined time param
                "queryTimeIntervalDelimiter": "/",                       // <-- start/end delimiter
                "queryTimeFormat": "yyyy-MM-ddTHH:mm:ssZ",
                "queryWindowInMin": 5,
                "queryParameters": { "format": "json" }
            },
            "paging": { "pagingType": "None" },
            "response": {
                "eventsJsonPaths": [                                     // <-- multiple paths
                    "$..messagesDelivered",
                    "$..messagesBlocked",
                    "$..clicksPermitted",
                    "$..clicksBlocked"
                ]
            }
        }
    }
}
```

This produces a query like: `?interval=2024-01-01T00:00:00Z/2024-01-01T00:05:00Z&format=json`

All four `eventsJsonPaths` are merged into a single event stream for ingestion.

---

## 8. BigID — Nested Steps / Multi-step Enrichment (Advanced)

**Source:** `Solutions/BigID/Data Connectors/BigIDDSPMLogs_ccp/`

**Why notable:** The most advanced pattern — chains 3 API calls per record. Primary call fetches cases, then enriches each with data source details and catalog objects. Uses `shouldJoinNestedData`, `stepCollectorConfigs`, `$placeholder$` syntax, and `extra.nestedTransformName`.

### PollingConfig (with step chain)

```json
{
    "name": "BigIDDSPMCatalog",
    "kind": "RestApiPoller",
    "properties": {
        "connectorDefinitionName": "BigIDDSPMLogsConnectorDefinition",
        "dcrConfig": {
            "dataCollectionEndpoint": "{{dataCollectionEndpoint}}",
            "dataCollectionRuleImmutableId": "{{dataCollectionRuleImmutableId}}",
            "streamName": "Custom-BigIDDSPMCatalog_CL"
        },
        "dataType": "BigIDDSPMCatalog_CL",
        "auth": {
            "type": "JwtToken",
            "UserToken": "{{bigidToken}}",
            "UserTokenPrepend": "",
            "TokenEndpoint": "https://{{bigidFqdn}}/api/v1/refresh-access-token",
            "TokenEndpointHttpMethod": "GET",
            "NoAccessTokenPrepend": true,
            "JwtTokenJsonPath": "$.systemToken"
        },
        "request": {
            "apiEndpoint": "https://{{bigidFqdn}}/api/v1/actionable-insights/all-cases",
            "rateLimitQPS": 20,
            "queryWindowInMin": 10,
            "httpMethod": "GET",
            "retryCount": 3,
            "timeoutInSeconds": 10,
            "headers": {
                "Accept": "application/json",
                "User-Agent": "BigID-MSFT-Sentinel-CCF-Connector (all-cases)"
            }
        },
        "response": {
            "eventsJsonPaths": ["$.data.cases"],
            "format": "json"
        },
        "paging": {
            "pagingType": "Offset",
            "pageSize": 50,
            "pageSizeParameterName": "limit",
            "offsetParaName": "offset"
        },

        // ---- Nested enrichment chain ----

        "shouldJoinNestedData": true,
        "joinedDataStepName": "dspmCase",
        "stepInfo": {
            "stepType": "Nested",
            "nextSteps": [{
                "stepId": "fetchDataSourceDetails",
                "stepPlaceholdersParsingKql": "source | project res = parse_json(data) | project dataSourceName = res.dataSourceName, policyName = res.policyName"
            }]
        },

        "stepCollectorConfigs": {
            // Step 2: Fetch data source details using $dataSourceName$ from step 1
            "fetchDataSourceDetails": {
                "shouldJoinNestedData": true,
                "joinedDataStepName": "datasource",
                "stepInfo": {
                    "stepType": "Nested",
                    "nextSteps": [{
                        "stepId": "fetchObjectsDetails",
                        "stepPlaceholdersParsingKql": "source"
                    }]
                },
                "request": {
                    "httpMethod": "GET",
                    "apiEndpoint": "https://{{bigidFqdn}}/api/v1/ds_connections/$dataSourceName$",
                    "queryParameters": { "withoutCredentialValue": "true" },
                    "headers": {
                        "Accept": "application/json",
                        "User-Agent": "BigID-MSFT-Sentinel-CCF-Connector (datasources)"
                    }
                },
                "response": {
                    "eventsJsonPaths": ["$.ds_connection"],
                    "format": "json"
                }
            },

            // Step 3: Fetch catalog objects using $dataSourceName$ and $policyName$
            "fetchObjectsDetails": {
                "shouldJoinNestedData": true,
                "joinedDataStepName": "expand",
                "request": {
                    "httpMethod": "GET",
                    "apiEndpoint": "https://{{bigidFqdn}}/api/v1/data-catalog/",
                    "queryParameters": {
                        "limit": 32,
                        "requireTotalCount": "true",
                        "filter": "SYSTEM = \"$dataSourceName$\" AND policy IN (\"$policyName$\")"
                    },
                    "headers": {
                        "Accept": "application/json",
                        "User-Agent": "BigID-MSFT-Sentinel-CCF-Connector (data-catalog)"
                    }
                },
                "response": {
                    "eventsJsonPaths": ["$.results"],
                    "format": "json"
                }
            }
        },

        "extra": {
            "nestedTransformName": "/ASI/Microsoft/MvExpandTransformer"
        }
    }
}
```

---

## Quick Reference: Pattern Lookup

| Pattern | Example Connector | Key Fields |
|---------|------------------|------------|
| Multi-connection, multi-table ASIM | Cisco Meraki | Multiple connections, `Microsoft-` outputStream |
| Multi-endpoint, shared stream | 1Password | Same `streamName` across connections, KQL `case()` to detect source |
| OAuth2 client_credentials | Auth0, Box | `GrantType: "client_credentials"`, `TokenEndpoint`, `TokenEndpointQueryParameters` |
| OAuth2 authorization_code | Azure DevOps | `GrantType: "authorization_code"`, `AuthorizationCode`, `RedirectUri`, `Scope` |
| startTime without endTime | Box | `StartTimeAttributeName` alone is valid |
| LinkHeader with rel link | Cisco Meraki | `linkHeaderRelLinkName: "rel=next"` or `"rel=prev"` |
| PersistentToken | Auth0, Box | `pagingType: "PersistentToken"`, server remembers cursor |
| POST with time window | 1Password | `httpMethod: "Post"`, `queryParametersTemplate`, `isPostPayloadJson: true` |
| Time interval parameter | Proofpoint TAP | `QueryTimeIntervalAttributeName`, `QueryTimeIntervalDelimiter` |
| Multiple eventsJsonPaths | Proofpoint TAP | Array of JSONPaths merging multiple response branches |
| Nested step enrichment | BigID | `shouldJoinNestedData`, `stepCollectorConfigs`, `$placeholder$` syntax |
| Basic auth | Jira | `type: "Basic"`, `UserName`, `Password` |
| JwtToken auth | BigID | `type: "JwtToken"`, `TokenEndpoint`, `JwtTokenJsonPath` |
| APIKey with Bearer prefix | 1Password | `ApiKeyIdentifier: "Bearer"` prepends to key value |
| Legacy APIPolling (v1) | Jira (old), Proofpoint TAP | `kind: "APIPolling"`, `pollingConfig`, `auth.authType` |
