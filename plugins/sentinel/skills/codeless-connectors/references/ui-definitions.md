# Connector UI Definitions Reference

Source: https://learn.microsoft.com/en-us/azure/sentinel/data-connector-ui-definitions-reference

## connectorUiConfig Structure

```json
{
    "kind": "Customizable",
    "properties": {
        "connectorUiConfig": {
            "id": "unique-id",
            "title": "Connector Title",
            "publisher": "Publisher Name",
            "descriptionMarkdown": "Description with **markdown**",
            "logo": "optional-svg-path",
            "graphQueriesTableName": "MyTable_CL",
            "graphQueries": [],
            "sampleQueries": [],
            "dataTypes": [],
            "connectivityCriteria": [],
            "availability": {},
            "permissions": {},
            "instructionSteps": []
        }
    }
}
```

## graphQueries
```json
"graphQueries": [{
    "metricName": "Total data received",
    "legend": "{{graphQueriesTableName}}",
    "baseQuery": "{{graphQueriesTableName}}"
}]
```

## sampleQueries
```json
"sampleQueries": [{
    "description": "All logs",
    "query": "{{graphQueriesTableName}}\n | sort by TimeGenerated\n | take 10"
}]
```
Sample queries only appear when: table exists, data has been ingested, `graphQueriesTableName` is set.

## dataTypes
```json
"dataTypes": [{
    "name": "{{graphQueriesTableName}}",
    "lastDataReceivedQuery": "{{graphQueriesTableName}}\n | summarize Time = max(TimeGenerated)\n | where isnotempty(Time)"
}]
```

## connectivityCriteria

### For Pull Connectors (RestApiPoller)
```json
"connectivityCriteria": [{ "type": "HasDataConnectors" }]
```

### For Push Connectors
```json
"connectivityCriteria": [{
    "type": "IsConnectedQuery",
    "value": ["MyTable_CL\n| summarize LastLogReceived = max(TimeGenerated)\n| project IsConnected = LastLogReceived > ago(7d)"]
}]
```

Use `isConnectivityCriteriasMatchSome: true` to OR multiple criteria.

## availability
```json
"availability": { "status": 1, "isPreview": false }
```
Status values: 1=Available, 2=FeatureFlag, 3=ComingSoon, 4=Internal

## permissions
```json
"permissions": {
    "resourceProvider": [{
        "provider": "Microsoft.OperationalInsights/workspaces",
        "permissionsDisplayText": "read and write permissions required.",
        "providerDisplayName": "Workspace",
        "scope": "Workspace",
        "requiredPermissions": { "write": true, "read": true, "delete": true }
    }],
    "customs": [{
        "name": "API credentials",
        "description": "An API key and secret are required."
    }]
}
```

Provider values: `Microsoft.OperationalInsights/workspaces`, `Microsoft.OperationalInsights/solutions`, `Microsoft.OperationalInsights/workspaces/datasources`, `microsoft.aadiam/diagnosticSettings`, `Microsoft.OperationalInsights/workspaces/sharedKeys`, `Microsoft.Authorization/policyAssignments`

Scope values: `Subscription`, `ResourceGroup`, `Workspace`

## instructionSteps — Authoring Rules

`instructionSteps` is the array of UI steps shown to the user when they open the connector
in the Microsoft Sentinel UI. There are four rules that, when broken, cause silent UX
failures (form fields appear optional, connect button never appears, parameters don't bind):

1. **`ConnectionToggleButton` MUST be the last element** of the `instructions` array in
   whichever step contains the credential Textboxes. Without it the user has no way to
   trigger connection setup. Use exact lowercase values: `"connectLabel": "connect"`,
   `"name": "connect"`.
2. **Every required Textbox MUST include `"validations": { "required": true }`.** Without
   this, fields appear optional in the UI even if the polling config can't function
   without them.
3. **Textbox `name` MUST exactly match the template-variable name** referenced in the
   polling config (`auth.ApiKey: "{{apiKey}}"` -> Textbox `name: "apiKey"`;
   `apiEndpoint: "https://{{oktaDomain}}/..."` -> Textbox `name: "oktaDomain"`). The
   parameter-consistency validator runs on deployment and rejects mismatches.
4. **No URL Textbox if `apiEndpoint` is fully hardcoded** (Tier 1). Only add a URL Textbox
   when the polling config contains `{{BaseUrl}}` or a named URL variable.

### Per-auth instruction-step templates

**APIKey** — extract the variable name from `auth.ApiKey` (e.g. `{{apiKey}}` -> `name: "apiKey"`):
```json
{
  "type": "Textbox",
  "parameters": {
    "label": "API Key",
    "placeholder": "Enter API Key",
    "type": "password",
    "name": "apiKey",
    "validations": { "required": true }
  }
}
```

**Basic** — username + password Textboxes:
```json
{ "type": "Textbox", "parameters": { "label": "Username", "type": "text", "name": "username", "validations": { "required": true } } },
{ "type": "Textbox", "parameters": { "label": "Password", "type": "password", "name": "password", "validations": { "required": true } } }
```

**OAuth2** — single `OAuthForm` element (no separate Textboxes for ClientId/Secret):
```json
{
  "type": "OAuthForm",
  "parameters": {
    "clientIdLabel": "Client ID",
    "clientSecretLabel": "Client Secret",
    "connectButtonLabel": "Connect",
    "disconnectButtonLabel": "Disconnect"
  }
}
```

**URL Textboxes** — only when `apiEndpoint` contains `{{...}}`:
```json
// For {{BaseUrl}} — placeholder is longest common URL prefix on path-segment boundaries
// (include any shared version prefix, e.g. https://api.openai.com/v1)
{
  "type": "Textbox",
  "parameters": { "label": "API Base URL", "placeholder": "https://api.vendor.com/v1", "type": "text", "name": "BaseUrl", "validations": { "required": true } }
}

// For named variables like {{oktaDomain}} — placeholder format matches how the variable
// is embedded; hostname-only when scheme is fixed
{
  "type": "Textbox",
  "parameters": { "label": "Okta Domain", "placeholder": "your-org.okta.com", "type": "text", "name": "oktaDomain", "validations": { "required": true } }
}
```

### graphQueries / dataTypes / sampleQueries — placeholder pattern

When the connector has a single primary table, set `graphQueriesTableName` once and use
`{{graphQueriesTableName}}` throughout the queries — the placeholder is substituted at
render time:

```json
"connectorUiConfig": {
    "graphQueriesTableName": "TechCorpEvents_CL",
    "graphQueries": [
        {
            "metricName": "Total events received",
            "legend": "{{graphQueriesTableName}}",
            "baseQuery": "{{graphQueriesTableName}} | where TimeGenerated > ago(14d) | summarize count() by bin(TimeGenerated, 1d)"
        }
    ],
    "dataTypes": [
        {
            "name": "{{graphQueriesTableName}}",
            "lastDataReceivedQuery": "{{graphQueriesTableName}} | summarize Time = max(TimeGenerated) | where isnotempty(Time)"
        }
    ],
    "sampleQueries": [
        { "description": "All events from the last 24 hours", "query": "{{graphQueriesTableName}} | where TimeGenerated > ago(24h) | take 100" },
        { "description": "Events by severity level", "query": "{{graphQueriesTableName}} | summarize count() by Severity | order by count_ desc" }
    ]
}
```

**Sample queries use TABLE column names (PascalCase), not API field names** — the
transform has already converted them by the time data hits the table.

For multi-table connectors, set `graphQueriesTableName` to the primary table and use
explicit table names in non-primary queries.

### Permissions object — per-auth `customs` templates

`resourceProvider` is always required (workspace read/write). `customs` documents the
external credentials the user needs to obtain; use the description pattern that matches
the auth type from the polling config:

| `auth.type` | `customs[].name`                   | Description pattern                                                        |
|-------------|------------------------------------|----------------------------------------------------------------------------|
| `APIKey`    | `{VendorName} API Key`             | "A {VendorName} API Key is required. [See documentation]({url})"           |
| `Basic`     | `{VendorName} Account Credentials` | "{VendorName} account credentials (username and password) are required."   |
| `OAuth2`    | `{VendorName} OAuth Application`   | "An OAuth2 application must be registered. Client ID and Secret required." |
| `JwtToken`  | `{VendorName} JWT Credentials`     | "{VendorName} JWT credentials (username and password) are required."       |

`tenant` is OPTIONAL — only add it for OAuth2 flows requiring admin consent:
`"tenant": ["GlobalAdmin", "SecurityAdmin"]`. `licenses` is OPTIONAL and should be OMITTED
for third-party connectors (it's only for Microsoft service integrations).

## Instruction Types

### Textbox
```json
{ "type": "Textbox", "parameters": { "label": "API Key", "placeholder": "Enter key", "type": "password", "name": "apikey" } }
```
Types: `text`, `password`, `number`, `email`. Each has `label`, `placeholder`, `type`, `name`.

### OAuthForm
```json
{
    "type": "OAuthForm",
    "parameters": {
        "UsernameLabel": "Client ID",
        "PasswordLabel": "Client Secret",
        "connectButtonLabel": "Connect",
        "disconnectButtonLabel": "Disconnect"
    }
}
```
Use even for non-OAuth auth — customizable labels make it work for any key+secret pair.

### ConnectionToggleButton
```json
{ "type": "ConnectionToggleButton", "parameters": { "connectLabel": "Connect", "name": "toggle" } }
```
Triggers DCR deployment based on connection parameters.

### CopyableLabel
```json
{
    "type": "CopyableLabel",
    "parameters": {
        "label": "Workspace ID and Key",
        "fillWith": ["WorkspaceId", "PrimaryKey"],
        "value": "Workspace: {0}, Key: {1}",
        "rows": 1,
        "wideLabel": false
    }
}
```
`fillWith` values: `workspaceId`, `workspaceName`, `primaryKey`, `MicrosoftAwsAccount`, `subscriptionId`, `TenantId`, `ApplicationId`, `ApplicationSecret`, `DataCollectionEndpoint`, `DataCollectionRuleId`

### Dropdown
```json
{
    "type": "Dropdown",
    "parameters": {
        "label": "Select option",
        "name": "dropdown",
        "options": [
            { "key": "opt1", "text": "Option 1" },
            { "key": "opt2", "text": "Option 2" }
        ],
        "placeholder": "Select...",
        "isMultiSelect": false,
        "required": true
    }
}
```

### Markdown
```json
{ "type": "Markdown", "parameters": { "content": "## Instructions\nUse **bold** and [links](https://example.com)." } }
```

### InfoMessage
```json
{ "type": "InfoMessage", "parameters": { "text": "Important information", "visible": true, "inline": true } }
```
`inline: true` = embedded in instructions (recommended). `inline: false` = blue background block.

### DataConnectorsGrid
```json
{
    "type": "DataConnectorsGrid",
    "parameters": {
        "mapping": [{ "columnName": "Name", "columnValue": "Value" }],
        "menuItems": ["MyConnector"]
    }
}
```

### ContextPane
```json
{
    "type": "ContextPane",
    "parameters": {
        "isPrimary": true,
        "label": "Add Account",
        "title": "Add Account",
        "subtitle": "Configure account",
        "contextPaneType": "DataConnectorsContextPane",
        "instructionSteps": [{
            "instructions": [
                { "type": "Textbox", "parameters": { "label": "Account ID", "type": "text", "name": "accountId", "validations": { "required": true } } },
                { "type": "Textbox", "parameters": { "label": "API Key", "type": "password", "name": "apikey", "validations": { "required": true } } }
            ]
        }]
    }
}
```

### DeployPushConnectorButton (Push only)
```json
{ "type": "DeployPushConnectorButton", "parameters": { "label": "Deploy connector resources", "applicationDisplayName": "My App" } }
```

### InstructionStepsGroup
```json
{
    "type": "InstructionStepsGroup",
    "parameters": {
        "title": "Advanced Configuration",
        "canCollapseAllSections": true,
        "expanded": false,
        "instructionSteps": [...]
    }
}
```

### InstallAgent
```json
{ "type": "InstallAgent", "parameters": { "linkType": "OpenCreateDataCollectionRule" } }
```
linkType values: `InstallAgentOnWindowsVirtualMachine`, `InstallAgentOnWindowsNonAzure`, `InstallAgentOnLinuxVirtualMachine`, `InstallAgentOnLinuxNonAzure`, `OpenSyslogSettings`, `OpenCustomLogsSettings`, `OpenWaf`, `OpenAzureFirewall`, `OpenMicrosoftAzureMonitoring`, `OpenFrontDoors`, `OpenCdnProfile`, `AutomaticDeploymentCEF`, `OpenAzureInformationProtection`, `OpenAzureActivityLog`, `OpenIotPricingModel`, `OpenPolicyAssignment`, `OpenAllAssignmentsBlade`, `OpenCreateDataCollectionRule`

## Multi-Table Connectors (ASIM)

When a connector routes data to multiple ASIM destination tables (e.g., `ASimNetworkSessionLogs`, `ASimWebSessionLogs`, `ASimAuditEventLogs`), the UI definition needs multiple `graphQueries` and `dataTypes` entries to show data status for each table.

### Pattern

1. Set `graphQueriesTableName` to one table (used as the default via `{{graphQueriesTableName}}`)
2. Add a `graphQueries` entry for each table/event type, referencing the table name directly (not via the placeholder) for non-default tables
3. Add vendor/product filters in each `baseQuery` so data from other vendors in shared ASIM tables is excluded
4. Add a `dataTypes` entry for each table with its own `lastDataReceivedQuery` including the same vendor filters

### Example (Cisco Meraki — 3 ASIM tables, 4 graph queries)

```json
{
    "graphQueriesTableName": "ASimNetworkSessionLogs",
    "graphQueries": [
        {
            "metricName": "Total IDS alerts received",
            "legend": "Get IDS Alerts",
            "baseQuery": "{{graphQueriesTableName}} | where EventProduct == \"Meraki\" and EventVendor == \"Cisco\""
        },
        {
            "metricName": "Total File Scanned events received",
            "legend": "Get File Scanned",
            "baseQuery": "ASimWebSessionLogs | where EventProduct == \"Meraki\" and EventVendor == \"Cisco\" and EventOriginalType == \"File Scanned\""
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
    ]
}
```

**Key points:**
- The `{{graphQueriesTableName}}` placeholder only resolves to the single value set in `graphQueriesTableName`. For additional tables, use the table name directly as a string.
- Always include vendor/product filters (e.g., `EventProduct == "Meraki"`) when targeting shared ASIM tables — otherwise you'll count data from other connectors.
- `sampleQueries` can use `union` to query across all tables: `union {{graphQueriesTableName}}, ASimWebSessionLogs, ASimAuditEventLogs | where EventProduct == "Meraki"`
