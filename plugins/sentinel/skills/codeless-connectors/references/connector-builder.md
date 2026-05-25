# Connector Builder Workflow

**When to use:** When building a new codeless connector from scratch — not fixing or modifying an existing template. Follow these phases sequentially, gathering all required information before generating output.

---

## Phase 1 — Destination & Data Foundation

### Step 1.1: Choose Destination Type

Ask the user which destination type they need:

| Destination | When to Use |
|-------------|-------------|
| **Custom Table** | New `_CL` table for vendor-specific data that doesn't map to a standard schema |
| **Custom to Native Table** | Route data to built-in Microsoft tables (e.g., `CommonSecurityLog`, `Syslog`) |
| **ASIM Parser** | Normalize data to an ASIM schema (e.g., `ASimNetworkSessionLogs`) |
| **UI Only** | Connector UI only — no DCE/DCR/table creation (e.g., for push connectors or agent-based collection) |

### Step 1.2: Configure Based on Destination

#### Custom Table Path

Gather the following:

1. **Table name** — must end with `_CL` suffix (e.g., `VendorAlerts_CL`)
2. **Table schema** — JSON array of `{name, type}` describing the final table columns
   - Common types: `string`, `int`, `long`, `real`, `bool`, `datetime`, `dynamic`, `guid`
   - Must include `TimeGenerated` (datetime)
3. **Table plan** — one of `Analytics`, `Basic`, or `Auxiliary` (from `table.schema.json` enum):
   - `Analytics` (default) — full KQL surface, billed per ingested GB, supports detections and alerts
   - `Basic` — lower cost, limited query surface (no joins/lookups against the table), best for high-volume logs you mostly forward and rarely query
   - `Auxiliary` — cheapest tier, KQL-only via search jobs and summary rules, NOT queryable interactively (only via search jobs or restoring to Analytics). Use for raw data you need to retain for compliance/forensics but rarely touch.
4. **Retention** — `retentionInDays` (4–730) for active queryable storage; `totalRetentionInDays` (4–4383) including archived storage
5. **DCE** — Data Collection Endpoint name; must be in the same region as the workspace
6. **DCR name** — Data Collection Rule name
7. **Stream name** — must start with `Custom-` prefix (e.g., `Custom-VendorAlerts_CL`)
8. **Stream declaration** — describes the **raw incoming data** shape (NOT the transformed output). If the API returns `ts`, `eventType`, `srcIp`, declare those exact names/types.
9. **transformKql** — KQL transformation from raw stream to destination table
   - Use `"source"` for pass-through (no transformation)
   - Must produce a `TimeGenerated` column
   - See `reference/kql-transforms.md` for supported functions

#### Custom to Native Table Path

Same as Custom Table, with these differences:

1. **No custom table creation** — target is an existing Microsoft table
2. **transformKql must include `outputStream`** mapping to `Microsoft-*` table name
3. **Multiple dataFlows** can route different event types to different native tables from a single stream

Example multi-dataFlow pattern:
```json
"dataFlows": [
    {
        "streams": ["Custom-RawEvents"],
        "destinations": ["clv2ws1"],
        "transformKql": "source | where EventType == 'auth' | project-rename ...",
        "outputStream": "Microsoft-CommonSecurityLog"
    },
    {
        "streams": ["Custom-RawEvents"],
        "destinations": ["clv2ws1"],
        "transformKql": "source | where EventType == 'syslog' | project-rename ...",
        "outputStream": "Microsoft-Syslog"
    }
]
```

#### ASIM Parser Path

1. **Select ASIM schema type** — reference `reference/asim-schemas.md` for all 10 schemas
2. **Choose normalization approach:**
   - **Ingest-time** (DCR transform) — normalize in `transformKql`, write directly to ASIM table
   - **Query-time** (saved search/function) — store raw data, create parser function for on-demand normalization
3. **Build normalization KQL** mapping source fields to ASIM fields
   - Every ASIM schema has mandatory fields that must be populated
   - Use `extend` to add computed fields, `project-rename` for direct mappings
4. **If ingest-time:** embed normalization in DCR `transformKql`, set `outputStream` to ASIM table (e.g., `Microsoft-ASimNetworkSessionLogs`)
5. **If query-time:** create a parser function with `functionAlias` for the workspace

ASIM destination tables:
- `ASimAuditEventLogs`, `ASimAuthenticationEventLogs`, `ASimDnsActivityLogs`
- `ASimDhcpEventLogs`, `ASimFileEventLogs`, `ASimNetworkSessionLogs`
- `ASimProcessEventLogs`, `ASimRegistryEventLogs`, `ASimUserManagementLogs`
- `ASimWebSessionLogs`

#### UI Only Path

Skip DCE/DCR/table creation entirely. Collect only connector metadata and jump directly to **Phase 4**.

---

## Phase 2 — API Polling Configuration

> Skip this phase for UI Only destination.

### Step 2.1: Request Configuration

Gather from the user:

| Property | Required | Description |
|----------|----------|-------------|
| `apiEndpoint` | Yes | Full URL to poll |
| `httpMethod` | No | `GET` (default) or `POST` |
| `queryWindowInMin` | No | Poll interval in minutes (default: 5) |
| `rateLimitQPS` | No | Max queries/second to respect API limits |
| `queryTimeFormat` | No | Date format for time parameters (default: ISO 8601 UTC) |
| `StartTimeAttributeName` | No | Query param name for window start time |
| `EndTimeAttributeName` | No | Query param name for window end time |
| `retryCount` | No | Retries on failure, 1-6 (default: 3) |
| `timeoutInSeconds` | No | Request timeout, 1-180 (default: 20) |
| `queryParameters` | No | Static query params for ongoing polling |
| `queryParametersTemplate` | No | Query params for connection validation |
| `headers` | No | Custom request headers |
| `isPostPayloadJson` | No | POST body as JSON (default: false) |

**Built-in variables** for query parameters:
- `{_QueryWindowStartTime}` — start of the current polling window
- `{_QueryWindowEndTime}` — end of the current polling window
- `{_APIKeyName}` — API key header name (in `queryParametersTemplate` only)
- `{_APIKey}` — API key value (in `queryParametersTemplate` only)

**Important:** API version in `queryParameters` can cause datetime translation issues — prefer adding the API version directly to the `apiEndpoint` URL.

### Step 2.2: Response Configuration

| Property | Required | Description |
|----------|----------|-------------|
| `eventsJsonPaths` | Yes | JSONPath to data array (e.g., `["$"]` or `["$.value"]`) |
| `format` | Yes | `json`, `csv`, or `xml` |
| `isGzipCompressed` | No | Response is gzip compressed |
| `successStatusJsonPath` | No | JSONPath to success indicator |
| `convertChildPropertiesToArray` | No | When API returns object instead of array |

**CSV-specific properties** (when `format` is `csv`):
- `CsvDelimiter` — field delimiter character
- `HasCsvBoundary` — CSV has boundary markers
- `HasCsvHeader` — first row is header
- `CsvEscape` — escape character

### Step 2.3: Pagination Configuration

Ask which pagination type the API uses:

| Type | When to Use |
|------|-------------|
| `None` | API returns all data in a single response |
| `LinkHeader` | Next page URL in response headers or body |
| `PersistentLinkHeader` | Like LinkHeader, persists cursor across query windows |
| `NextPageToken` | Token/cursor for next page in response body |
| `PersistentToken` | Token persists server-side across requests |
| `NextPageUrl` | Full next-page URL in response body |
| `Offset` | Skip/offset parameter for page navigation |
| `CountBasedPaging` | Page number parameter |

See `reference/pagination-types.md` for type-specific configuration properties.

**Note:** `PersistentLinkHeader` only allows one concurrent query to avoid race conditions.

---

## Phase 3 — Authentication Configuration

> Skip this phase for UI Only destination.

### Step 3.1: Choose Auth Type

| Type | When to Use |
|------|-------------|
| `Basic` | Username + password |
| `APIKey` | API key in header or POST body |
| `OAuth2` | `authorization_code` or `client_credentials` grant |
| `JwtToken` | JWT token via username/password endpoint |

See `reference/authentication-types.md` for full property details and examples.

### Step 3.2: Gather Auth-Specific Parameters

#### Basic
- Username parameter name
- Password parameter name

#### APIKey
- API key parameter name
- `ApiKeyName` — header name (default: `Authorization`)
- `ApiKeyIdentifier` — prefix (default: `token`)
- `IsApiKeyInPostPayload` — send in POST body instead

#### OAuth2
- `GrantType` — `authorization_code` or `client_credentials`
- `TokenEndpoint` — token exchange URL
- `Scope` — required scopes
- For authorization_code: `AuthorizationEndpoint`, `RedirectUri`
- `IsCredentialsInHeaders` — send credentials in header vs body
- `TokenEndpointQueryParameters` — custom params for token request
- `AuthorizationEndpointQueryParameters` — custom params for auth request

#### JwtToken
- `TokenEndpoint` — URL to obtain JWT
- Username/password key-value pairs (or `UserToken` for pre-existing tokens)
- `IsCredentialsInHeaders` — Basic Auth header vs POST body
- `IsJsonRequest` — JSON vs form-encoded body
- `JwtTokenJsonPath` — JSONPath to extract token from response

### Step 3.3: ARM Parameter Setup

All credentials must use `securestring` type:
```json
"parameters": {
    "apiKey": {
        "defaultValue": "",
        "type": "securestring",
        "minLength": 1,
        "metadata": { "description": "Enter the API key." }
    }
}
```

---

## Phase 4 — Connector UI Metadata

Gather the following for the connector definition:

### Step 4.1: Basic Metadata
- **title** — display name in Sentinel
- **publisher** — company/organization name
- **descriptionMarkdown** — markdown description of the connector
- **logo** — optional SVG icon

### Step 4.2: Queries and Data Types
- **graphQueriesTableName** — set to your actual destination table name
- **graphQueries** — array of metric queries:
  ```json
  [{"metricName": "Total data received", "legend": "{{graphQueriesTableName}}", "baseQuery": "{{graphQueriesTableName}}"}]
  ```
- **sampleQueries** — array of example queries:
  ```json
  [{"description": "All logs", "query": "{{graphQueriesTableName}}\n | sort by TimeGenerated\n | take 10"}]
  ```
- **dataTypes** — array of data type definitions:
  ```json
  [{"name": "{{graphQueriesTableName}}", "lastDataReceivedQuery": "{{graphQueriesTableName}}\n | summarize Time = max(TimeGenerated)\n | where isnotempty(Time)"}]
  ```

### Step 4.3: Connectivity and Permissions
- **connectivityCriteria type:**
  - `HasDataConnectors` — for pull/RestApiPoller connectors
  - `IsConnectedQuery` — for push connectors
- **permissions** — required Azure permissions:
  ```json
  "permissions": {
      "resourceProvider": [{
          "provider": "Microsoft.OperationalInsights/workspaces",
          "permissionsDisplayText": "Read and Write permissions on the workspace",
          "providerDisplayName": "Workspace",
          "scope": "Workspace",
          "requiredPermissions": { "read": true, "write": true, "delete": true }
      }]
  }
  ```

### Step 4.4: Instruction Steps
Build the `instructionSteps` array. Common patterns by auth type:

**For APIKey:**
```json
[
    {"type": "Textbox", "parameters": {"label": "API Key", "type": "password", "name": "apiKey"}},
    {"type": "Textbox", "parameters": {"label": "API Endpoint", "type": "text", "name": "endpoint"}},
    {"type": "ConnectionToggleButton", "parameters": {"connectLabel": "Connect", "name": "toggle"}}
]
```

**For OAuth2:**
```json
[
    {"type": "OAuthForm", "parameters": {
        "clientIdLabel": "Client ID",
        "clientSecretLabel": "Client Secret",
        "connectButtonLabel": "Connect",
        "disconnectButtonLabel": "Disconnect"
    }}
]
```

**For guidance text:**
```json
[
    {"type": "InfoMessage", "parameters": {"text": "Important setup instructions here."}},
    {"type": "Markdown", "parameters": {"content": "## Step 1\nFollow these steps..."}}
]
```

See `reference/ui-definitions.md` for all instruction types and their properties.

---

## Phase 5 — Assemble ARM Template

Follow the 5-resource pattern from `reference/arm-template-structure.md`.

### Step 5.1: Template Skeleton
```json
{
    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
    "contentVersion": "1.0.0.0",
    "parameters": { /* workspace, credentials, endpoint params */ },
    "variables": {
        "_solutionName": "Vendor Solution Name",
        "_solutionVersion": "3.0.0",
        "_solutionId": "vendor-connector-id",
        /* contentId, templateName variables for each resource */
    },
    "resources": [ /* 5 resources in dependency order */ ]
}
```

### Step 5.2: Populate Resources
1. **contentPackages** — solution container (deploy first)
2. **contentTemplates #1** — nested template containing DCR, custom table(s), metadata
3. **dataConnectorDefinitions** — connector UI config
4. **metadata** — links resources together
5. **contentTemplates #2** — nested template containing RestApiPoller connection rules

### Step 5.3: Apply Escaping Rules
- Single `[` — parent template, evaluated at deploy time
- Double `[[` — nested templates, evaluated at connect time
- All ARM functions in nested templates need `[[`: `concat()`, `resourceId()`, `subscription()`, `resourceGroup()`, `parameters()`, etc.
- Closing bracket is NOT doubled

### Step 5.4: Slot in Configuration Objects
- Insert `request`, `response`, `paging` objects into connection rules
- Insert `auth` object with `[[parameters('...')` references
- Ensure `_solutionVersion` is `3.0.0` or above
- Set `dcrConfig` with stream name and DCR immutable ID references

### Step 5.5: Variables Section
Construct variables for all resource cross-references:
```json
"variables": {
    "_solutionId": "uniqueVendorId",
    "_solutionVersion": "3.0.0",
    "_solutionName": "Vendor Name",
    "dataConnectorVersionConnectorDefinition": "1.0.0",
    "dataConnectorVersionConnections": "1.0.0",
    "_dataConnectorContentIdConnectorDefinition": "VendorConnectorDefinition",
    "_dataConnectorContentIdConnections": "VendorConnectorConnections",
    "dataConnectorTemplateNameConnectorDefinition": "[concat(variables('_dataConnectorContentIdConnectorDefinition'), '-dc')]",
    "dataConnectorTemplateNameConnections": "[concat(variables('_dataConnectorContentIdConnections'), '-dc')]"
}
```

---

## Phase 6 — Build createUiDefinition.json

> Reference `reference/create-ui-definition.md` for full details.

Generate the Azure Marketplace deployment UI for the ARM template:

1. Map each ARM template `parameter` to a UI element
2. Create logical step groupings (Basics, Configuration, Credentials)
3. Add validation (regex, required fields)
4. Wire `outputs` to ARM parameter names

---

## Phase 7 — Review & Validate

Before presenting the final output, verify:

### Checklist
```
[ ] Title, Publisher, Description set correctly
[ ] DCE created/selected (same region as workspace)
[ ] DCR configured with correct stream declarations
[ ] Stream name has Custom- prefix
[ ] Table name has _CL suffix (if custom table)
[ ] DCR immutable ID referenced correctly
[ ] Request config: apiEndpoint, httpMethod, time params set
[ ] Response config: eventsJsonPaths, format set
[ ] Auth config: correct type with all required fields
[ ] Paging config: matches API pagination behavior
[ ] Graph queries reference correct table
[ ] Sample queries are valid KQL
[ ] Permissions include workspace read/write
[ ] Instruction steps match auth type
[ ] ARM escaping: single [ at parent, [[ in nested templates
[ ] securestring for all credentials
[ ] _solutionVersion is 3.0.0+
[ ] transformKql uses only supported KQL functions
[ ] TimeGenerated produced by every transform
[ ] No blank lines in KQL strings
[ ] Stream declarations match raw incoming data shape
```

### Cross-Reference
- Walk through the full **Deployment Checklist** in `SKILL.md`
- Verify all **Success Criteria** from `SKILL.md` top
- If any criterion fails, revise and re-check (up to 5 iterations)
