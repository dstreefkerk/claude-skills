# ARM Template Structure Reference

## Five Required Resources

### Resource 1: contentTemplates (Connector Definition + DCR + Table + Metadata)
```json
{
    "type": "Microsoft.OperationalInsights/workspaces/providers/contentTemplates",
    "apiVersion": "2023-04-01-preview",
    "dependsOn": ["[extensionResourceId(..., 'contentPackages', variables('_solutionId'))]"],
    "properties": {
        "contentId": "[variables('_dataConnectorContentIdConnectorDefinition')]",
        "contentKind": "DataConnector",
        "mainTemplate": {
            // Nested template containing (all four required):
            // - Microsoft.OperationalInsights/workspaces/providers/dataConnectorDefinitions resource
            // - Microsoft.OperationalInsights/workspaces/providers/metadata resource
            // - Microsoft.Insights/dataCollectionRules resource
            // - Microsoft.OperationalInsights/workspaces/tables resource(s)
        },
        "packageKind": "Solution",
        "packageVersion": "[variables('_solutionVersion')]",
        "contentSchemaVersion": "3.0.0"
    }
}
```

### Resource 2: dataConnectorDefinitions (UI)
```json
{
    "type": "Microsoft.OperationalInsights/workspaces/providers/dataConnectorDefinitions",
    "apiVersion": "2022-09-01-preview",
    "kind": "Customizable",
    "properties": {
        "connectorUiConfig": { /* UI definition */ }
    }
}
```

### Resource 3: metadata
```json
{
    "type": "Microsoft.OperationalInsights/workspaces/providers/metadata",
    "apiVersion": "2022-01-01-preview",
    "properties": {
        "parentId": "[extensionResourceId(..., 'dataConnectorDefinitions', ...)]",
        "contentId": "...",
        "kind": "DataConnector",
        "source": { "kind": "Solution" },
        "dependencies": {
            "criteria": [{
                "kind": "ResourcesDataConnector",
                "contentId": "...",
                "version": "..."
            }]
        }
    }
}
```

### Resource 4: contentTemplates (Connection Rules)
```json
{
    "type": "Microsoft.OperationalInsights/workspaces/providers/contentTemplates",
    "apiVersion": "2023-04-01-preview",
    "dependsOn": ["[extensionResourceId(..., 'contentPackages', variables('_solutionId'))]"],
    "properties": {
        "contentId": "[variables('_dataConnectorContentIdConnections')]",
        "contentKind": "ResourcesDataConnector",
        "mainTemplate": {
            "parameters": {
                "connectorDefinitionName": { "type": "string" },
                "workspace": { "type": "string" },
                "dcrConfig": { "type": "object" }
                // + your custom params (apikey, domain, etc.)
            },
            "resources": [
                // metadata resource
                // Microsoft.OperationalInsights/workspaces/providers/dataConnectors
                //   kind: "RestApiPoller"
            ]
        },
        "contentSchemaVersion": "3.0.0"
    }
}
```

### Resource 5: contentPackages (Solution Container)
```json
{
    "type": "Microsoft.OperationalInsights/workspaces/providers/contentPackages",
    "apiVersion": "2023-04-01-preview",
    "properties": {
        "version": "[variables('_solutionVersion')]",
        "kind": "Solution",
        "contentSchemaVersion": "3.0.0",
        "contentId": "[variables('_solutionId')]",
        "source": { "kind": "Solution" },
        "dependencies": {
            "operator": "AND",
            "criteria": [{ "kind": "DataConnector" }]
        },
        "firstPublishDate": "YYYY-MM-DD",
        "contentKind": "Solution",
        "packageId": "[variables('_solutionId')]",
        "contentProductId": "[concat(take(variables('_solutionId'), 50),'-','sl','-', uniqueString(concat(variables('_solutionId'),'-','Solution','-',variables('_solutionId'),'-', variables('_solutionVersion'))))]"
    }
}
```

> **Required**: `contentProductId` and `packageId` are mandatory on contentPackages. Omitting them causes `BadRequestException: properties.contentProductId is required` at deploy time.

## Standard Parameters
```json
"parameters": {
    "location": { "type": "string", "defaultValue": "[resourceGroup().location]" },
    "workspace-location": { "type": "string", "defaultValue": "" },
    "subscription": { "defaultValue": "[last(split(subscription().id, '/'))]", "type": "string" },
    "resourceGroupName": { "defaultValue": "[resourceGroup().name]", "type": "string" },
    "workspace": { "defaultValue": "", "type": "string" }
}
```

## Standard Variables
```json
"variables": {
    "workspaceResourceId": "[resourceId('microsoft.OperationalInsights/Workspaces', parameters('workspace'))]",
    "_solutionName": "My Solution",
    "_solutionVersion": "3.0.0",
    "_solutionAuthor": "Author Name",
    "_solutionId": "azuresentinel.azure-sentinel-solution-azuresentinel.azure-sentinel-MySolution",
    "_solutionTier": "Community",
    "dataConnectorVersionConnectorDefinition": "1.0.0",
    "dataConnectorVersionConnections": "1.0.0",
    "_dataConnectorContentIdConnectorDefinition": "MyConnectorDefinition",
    "_dataConnectorContentIdConnections": "MyConnectorConnections",
    "dataConnectorTemplateNameConnectorDefinition": "[concat(parameters('workspace'),'-dc-',uniquestring(variables('_dataConnectorContentIdConnectorDefinition')))]",
    "dataConnectorTemplateNameConnections": "[concat(parameters('workspace'),'-dc-',uniquestring(variables('_dataConnectorContentIdConnections')))]",
    "_logAnalyticsTableId1": "MyTable_CL"
}
```

## Escaping Rules

### The Core Rule
`[[` tells ARM: "don't evaluate now — pass as literal for later evaluation."

### Escaping by Context
| Expression Location | Syntax | Why |
|---------------------|--------|-----|
| Parent template, deploy-time | `"[parameters('x')]"` | ARM evaluates immediately |
| Nested mainTemplate, deploy-time DCR | `"[variables('workspaceResourceId')]"` | Still evaluated at deploy |
| Nested mainTemplate, connect-time connector | `"[[parameters('x')]"` | Deferred to connect time |
| Any ARM function in nested connector props | `"[[concat('https://',parameters('domain'),'/api')]"` | Deferred |

### What Gets Double-Bracketed
Everything in the RestApiPoller `properties` block within the second contentTemplates resource:
- `"[[parameters('apikey')]"` — user-provided credentials
- `"[[parameters('dcrConfig').dataCollectionEndpoint]"` — DCR config
- `"[[parameters('dcrConfig').dataCollectionRuleImmutableId]"` — DCR immutable ID
- `"[[concat(...)]"` — constructed URLs from user params

### What Stays Single-Bracketed
- DCR's `workspaceResourceId` in `destinations.logAnalytics` — evaluated at ARM deploy time
- DCR's `dataCollectionEndpointId` — evaluated at deploy time
- Resource names, locations, dependsOn references

### Table Resource Naming in Content Templates
Table resources (`Microsoft.OperationalInsights/workspaces/tables`) inside
`contentTemplates.mainTemplate` must use **only the table name** — NOT the
compound `workspace/tableName` form. The Sentinel Portal scopes REST API
calls to the workspace automatically. Including the workspace prefix causes
double-nesting (e.g. `/workspaces/{ws}/tables/{ws}/Table_CL`) and a 404.

- `"name": "MyTable_CL"` — correct
- `"name": "[concat(parameters('workspace'), '/MyTable_CL')]"` — wrong, causes 404

### Variable Scoping
Parent template variables are NOT accessible in nested `mainTemplate` blocks. Solutions:
1. Re-declare needed variables in the nested template's `variables` section
2. Pass values as parameters to the nested template
3. For the connection template, use `"[[parameters('x')]"` for user-collected values

## Dependency Chains
- Resources 1 and 4 (contentTemplates) depend on Resource 5 (contentPackages)
- Always use explicit `dependsOn` -- ARM doesn't guarantee ordering without them
- Omitting `dependsOn` causes intermittent "package cannot be found" errors

## Content Template Dependency Rules

- **ConnectorDefinition contentTemplate** (`contentKind: "DataConnector"`) must depend ONLY on contentPackages. Never add a dependency on the Connections contentTemplate (`contentKind: "ResourcesDataConnector"`). A reversed dependency causes "content template $XxxDefinition not found" at Connect time.
- **Connections contentTemplate** (`contentKind: "ResourcesDataConnector"`) must depend ONLY on contentPackages.
- **Connections metadata `parentId`**: For single-poller connectors, point to the `dataConnectors/<name>` resource. For multi-poller connectors, point to the `dataConnectorDefinitions/<name>` resource (since there is no single poller resource to reference).
- **`contentProductId` prefixes**: Use `'sl'` for Solution (contentPackages), `'dc'` for DataConnector (ConnectorDefinition contentTemplate), `'rdc'` for ResourcesDataConnector (Connections contentTemplate). Using the wrong prefix causes the Portal to look in the wrong content category.
- **Table resources inside nested `mainTemplate`**: Must NOT have a `kind` property (omit it entirely) and must NOT have a `location` property (the Content Hub scopes automatically).

## Top-Level Tables (Required)

Custom tables MUST be deployed as **top-level resources** in the outer ARM template, in addition to being defined inside the `contentTemplate.mainTemplate`. Without top-level tables, the Connect button fails with `InvalidOutputTable` because the DCR references tables that don't yet exist -- tables inside a contentTemplate are only a stored definition, not actually deployed.

**Top-level table naming** (outside contentTemplates):
```json
{
    "type": "Microsoft.OperationalInsights/workspaces/tables",
    "name": "[concat(parameters('workspace'), '/', variables('_logAnalyticsTableId1'))]",
    "apiVersion": "2022-10-01",
    "properties": {
        "schema": { ... },
        "retentionInDays": 90,
        "totalRetentionInDays": 90
    }
}
```

**Nested table naming** (inside contentTemplate mainTemplate):
```json
{
    "type": "Microsoft.OperationalInsights/workspaces/tables",
    "name": "MyTable_CL",
    "apiVersion": "2022-10-01",
    "properties": { ... }
}
```

Key differences:
- Top-level uses `concat(parameters('workspace'), '/', tableName)` -- workspace prefix required
- Nested uses just the table name -- the Portal adds workspace scoping automatically
- Nested tables must NOT have `kind` or `location` properties
