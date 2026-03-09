# CCF Packaging Details

CCF-specific rules for the `createSolutionV3.ps1` packaging tool. For general packaging workflow, see `reference/packaging.md`. For script usage, see `scripts/README.md`.

---

## Folder Naming Convention

CCF connector files must live in a folder following this pattern:

```
{CompanyName}{ProductName}{LogType}Logs_ccf
```

**Example:** For "Palo Alto Prisma Cloud CWPP":
- CompanyName: `PaloAlto`
- ProductName: `PrismaCloudCWPP`
- LogType: `Logs` (or specific type like `SysLogs`, `CustomLogs`)
- Result: `PaloAltoPrismaCloudCWPPLogs_ccf`

> **Note:** Older connectors in the repo use `_ccp` or `_CCP` as the folder suffix. The current convention is `_ccf`. Both are accepted by the packager.

The folder goes under `Data Connectors/`:
```
Solutions/{SolutionName}/Data Connectors/{CompanyProduct}Logs_ccf/
```

## File Suffix Requirements

Files inside the CCF folder must use these suffixes:

| File Type | Required Suffix | Example |
|-----------|----------------|---------|
| Connector Definition | `_connectorDefinition` | `PaloAltoPrismaCloudCWPP_connectorDefinition.json` |
| Poller Config | `_PollerConfig` | `PaloAltoPrismaCloudCWPP_PollerConfig.json` |
| Data Collection Rule | `_DCR` | `PaloAltoPrismaCloudCWPP_DCR.json` |
| Table (optional) | `_Table` | `PaloAltoPrismaCloudCWPP_Table.json` |

## Data Connectors Array Rule

In the solution data file (`Solution_{Name}.json`), the `Data Connectors` array should **only specify the path to the definition file**. The packager auto-discovers the corresponding poller, DCR, and table files by reading the cross-file mappings.

```json
{
  "Data Connectors": [
    "Data Connectors/PaloAltoPrismaCloudCWPPLogs_ccf/PaloAltoPrismaCloudCWPP_connectorDefinition.json"
  ]
}
```

For multiple CCF connectors, add multiple definition file paths to the array.

## Cross-File Mapping

These identifiers must match across files — mismatches cause packaging or deployment failures:

```
ConnectorDefinition
  └─ connectorUiConfig.id = "MyConnectorId"
       │
       ▼
PollerConfig
  └─ properties.connectorDefinitionName = "MyConnectorId"    ← must match definition id
  └─ properties.dcrConfig.streamName = "Custom-MyStream"
       │
       ▼
DCR
  └─ properties.streamDeclarations."Custom-MyStream"         ← must match poller streamName
  └─ properties.dataFlows[].streams = ["Custom-MyStream"]
  └─ properties.dataFlows[].outputStream = "Custom-MyTable_CL"
       │
       ▼
Table
  └─ properties.schema.name = "MyTable_CL"                  ← must match DCR outputStream (minus Custom- prefix)
  └─ name = "MyTable_CL"                                    ← must equal schema.name
```

**Key rules:**
- Definition `name` and `connectorUiConfig.id` should be the same value
- Poller `connectorDefinitionName` must exactly match definition `id`
- Stream names must start with `Custom-` prefix
- Table `name` and `schema.name` must be identical
- If using a standard table (e.g., `Microsoft-ASimNetworkSessionLogs`), no table file or `outputStream` is needed

## DCR Name Length Constraint

The DCR `name` property must be short. On deployment, the full name becomes:

```
Microsoft-Sentinel-{DCR-name}-{workspaceName}-{randomValue}
```

**Total limit: 65 characters.** If exceeded, the DCR silently fails to create. Always verify DCR creation in the Azure portal after deployment (search "Data Collection Rules").

## Standard Stream Mappings

For standard Log Analytics tables, the stream name in the poller must map to the correct DCR stream name. These mappings are defined in `scripts/common/standardLogStreams.ps1`:

- **Key** = poller file `streamName` (e.g., `Custom-ASimNetworkSessionLogs`)
- **Value** = DCR `streams` value (e.g., `Microsoft-ASimNetworkSessionLogs`)

If the stream mapping doesn't match an entry in `standardLogStreams.ps1`, packaging fails with a stream mismatch error.

Standard tables (prefixed with `Microsoft-`) do not need:
- A table file
- The `outputStream` property in the DCR

## Connector Kinds

### RestApiPoller (most common)
Sentinel polls the source API on a schedule. See `reference/request-response-config.md` for full property reference.

### StorageAccountBlobContainer
Polls Azure Blob Storage via Event Grid. The connector definition **must** include these specific `name` values in instruction step parameters — the packager uses them to generate additional ARM resources:
- `principalId`
- `blobContainerUri`
- `StorageAccountLocation`
- `StorageAccountResourceGroupName`
- `StorageAccountSubscription`
- `EGSystemTopicName`

The packager auto-generates ARM resources for: storage queues (notification + dead-letter), Event Grid system topic and subscription, and role assignments. See `scripts/common/storageAccountDeploymentTemplate.ps1`.

### WebSocket
Same properties as RestApiPoller, but `apiEndpoint` must begin with `wss://`.
- Example: [Proofpoint On Demand](https://github.com/Azure/Azure-Sentinel/blob/master/Solutions/Proofpoint%20On%20demand(POD)%20Email%20Security/Data%20Connectors/ProofPointEmailSecurity_CCP/ProofpointPOD_PollingConfig.json)

### GCP
Pre-configured for Google Cloud Platform sources.
- Example: [GCP Audit Logs](https://github.com/Azure/Azure-Sentinel/blob/master/Solutions/Google%20Cloud%20Platform%20Audit%20Logs/Data%20Connectors/GCPAuditLogs_ccp/data_connector_poller.json)
- Reference: [GCP data connector REST API](https://learn.microsoft.com/en-us/rest/api/securityinsights/data-connectors/create-or-update?view=rest-securityinsights-2024-01-01-preview&tabs=HTTP#gcpdataconnector)

### AmazonWebServicesS3
For AWS S3-based log sources. Supports dropdown-driven dynamic stream names (see below).
- Examples: [AWS WAF](https://github.com/Azure/Azure-Sentinel/blob/master/Solutions/Amazon%20Web%20Services/Data%20Connectors/AWS_WAF_CCP/AwsS3_WAF_PollingConfig.json), [VMware Carbon Black](https://github.com/Azure/Azure-Sentinel/blob/master/Solutions/VMware%20Carbon%20Black%20Cloud/Data%20Connectors/VMwareCarbonBlackCloud_ccp/CarbonBlack_PollingConfig.json)
- Reference: [AWS S3 data connector REST API](https://learn.microsoft.com/en-us/rest/api/securityinsights/data-connectors/create-or-update?view=rest-securityinsights-2024-01-01-preview&tabs=HTTP#awscloudtraildataconnector)

## Multi-Poller Pattern

A single definition file can serve multiple pollers. Place multiple JSON objects in a single poller file array:

```json
[
  {
    "name": "PollerForAlerts",
    "kind": "RestApiPoller",
    "properties": {
      "connectorDefinitionName": "SharedDefinitionId",
      "dcrConfig": { "streamName": "Custom-AlertsStream" },
      ...
    }
  },
  {
    "name": "PollerForEvents",
    "kind": "RestApiPoller",
    "properties": {
      "connectorDefinitionName": "SharedDefinitionId",
      "dcrConfig": { "streamName": "Custom-EventsStream" },
      ...
    }
  }
]
```

**Rules:**
- Each poller `name` must be unique within the file
- All pollers must reference the same `connectorDefinitionName`
- Each poller can target a different stream/table
- The DCR file should contain corresponding `dataFlows` entries for each stream
- Keep the single definition file at the root of `Data Connectors/`, with poller/DCR/table files in subfolders

## Dropdown-Driven Dynamic Stream Names

For `AmazonWebServicesS3` kind: if the connector definition includes a `Dropdown` instruction type, the packager dynamically maps dropdown options to stream names.

In the poller file, set `streamName` to any default value from the DCR. The packager replaces it with a dynamic expression based on the dropdown selection in the generated `mainTemplate.json`.

## Comma-Separated Copy Pattern

To generate multiple instances of a single ARM template resource (e.g., one poller per metric type), use a **comma-separated** string in the connector definition's `description` field.

The packager:
1. Detects the comma-separated pattern
2. Inserts an ARM `copy` object with `name` and `count` properties
3. Adds a `commaSeparatedArray` variable using `[[split(parameters('paramName'), ',')]]`

This creates one ARM resource instance per comma-separated value.

## Textbox Validation

In connector definition instruction steps, textbox parameters support a `validations` object:

```json
{
  "parameters": {
    "label": "API Key",
    "type": "text",
    "name": "apiKey",
    "validations": {
      "required": true
    }
  },
  "type": "Textbox"
}
```

**Packaging behavior:**
- `"required": true` — generates an ARM parameter with `minLength: 1` (adds asterisk to label)
- `"required": false` — generates an ARM parameter with `defaultValue: ""` and no `minLength`

## Building Block JSON Templates

### Connector Definition
```json
{
  "type": "Microsoft.SecurityInsights/dataConnectorDefinitions",
  "apiVersion": "2022-09-01-preview",
  "name": "<NameWithoutSpaces>",
  "location": "{{location}}",
  "kind": "Customizable",
  "properties": {
    "connectorUiConfig": {
      "id": "<NameWithoutSpaces>",
      "title": "<Display Title>",
      "publisher": "<Publisher>",
      "descriptionMarkdown": "<Description>",
      "graphQueriesTableName": "<TableName_CL>",
      "graphQueries": [{ "metricName": "Total events received", "legend": "<Legend>", "baseQuery": "{{graphQueriesTableName}}" }],
      "sampleQueries": [{ "description": "Get Sample Events", "query": "{{graphQueriesTableName}}\n | take 10" }],
      "dataTypes": [{ "name": "{{graphQueriesTableName}}", "lastDataReceivedQuery": "{{graphQueriesTableName}}\n | where TimeGenerated > ago(12h) | summarize Time = max(TimeGenerated)\n | where isnotempty(Time)" }],
      "connectivityCriteria": [{ "type": "HasDataConnectors" }],
      "availability": { "isPreview": false },
      "permissions": { "resourceProvider": [] },
      "instructionSteps": []
    }
  }
}
```

### Poller Config (RestApiPoller)
```json
[{
  "type": "Microsoft.SecurityInsights/dataConnectors",
  "apiVersion": "2022-10-01-preview",
  "name": "<PollerName>",
  "kind": "RestApiPoller",
  "properties": {
    "connectorDefinitionName": "<MatchesDefinitionId>",
    "dataType": "<TableName_CL>",
    "dcrConfig": {
      "streamName": "Custom-<StreamName>"
    },
    "auth": { },
    "request": { },
    "response": {
      "eventsJsonPaths": ["$"],
      "format": "json"
    },
    "paging": { }
  }
}]
```

### DCR
```json
[{
  "name": "<ShortNameNoSpaces>",
  "apiVersion": "2021-09-01-preview",
  "type": "Microsoft.Insights/dataCollectionRules",
  "location": "{{location}}",
  "properties": {
    "dataCollectionEndpointId": "{{dataCollectionEndpointId}}",
    "streamDeclarations": {
      "Custom-<StreamName>": {
        "columns": [
          { "name": "TimeGenerated", "type": "datetime" },
          { "name": "columnName", "type": "string" }
        ]
      }
    },
    "destinations": {
      "logAnalytics": [{ "workspaceResourceId": "{{workspaceResourceId}}", "name": "clv2ws1" }]
    },
    "dataFlows": [{
      "streams": ["Custom-<StreamName>"],
      "destinations": ["clv2ws1"],
      "transformKql": "source",
      "outputStream": "Custom-<TableName_CL>"
    }]
  }
}]
```

### Table
```json
[{
  "name": "<TableName_CL>",
  "type": "Microsoft.OperationalInsights/workspaces/tables",
  "apiVersion": "2021-03-01-privatepreview",
  "properties": {
    "schema": {
      "name": "<TableName_CL>",
      "columns": [
        { "name": "TimeGenerated", "type": "datetime", "isDefaultDisplay": true, "description": "Event timestamp" },
        { "name": "columnName", "type": "string", "description": "Column description" }
      ]
    }
  }
}]
```

**Notes:**
- Table `name` must NOT include the `Custom-` prefix (that's only for stream references in the DCR)
- The `_CL` suffix is required for custom tables
- `workspaceResourceId` is optional in the DCR — if omitted, the packager inserts `[resourceId('microsoft.OperationalInsights/Workspaces', parameters('workspace'))]`
- `{{location}}` placeholders are replaced with ARM parameter references during packaging

## Post-Deployment Verification

After deploying via Custom Deployment or Partner Center:

1. Navigate to the deployed workspace > **Data Connectors** blade
2. Search for and open the connector page
3. **Before clicking Connect**: open browser Developer Tools (`Ctrl+F12`) > **Network** tab
4. Click **Connect** — this triggers table creation (if present) then DCR creation
5. Verify table: Log Analytics workspace > Tables blade > search for your table name
6. Verify DCR: Azure portal global search > "Data Collection Rules" > search for the DCR `name` value from your source file
7. If DCR is missing: check the Network tab for `batch` requests with `PUT` method — response errors indicate the cause (most commonly: name length > 65 chars or stream mapping mismatches)
8. Success indicator: "Connect Connected" notification popup
