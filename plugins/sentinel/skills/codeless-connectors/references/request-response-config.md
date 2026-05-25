# Request, Response, and DCR Configuration Reference

## Endpoint URL Strategy — Three-Tier Rule

`apiEndpoint` can be hardcoded, parameterised by a named variable, or built from a generic
`{{BaseUrl}}` placeholder. **When in doubt, default to Tier 3 (`{{BaseUrl}}`)** — an
unnecessary user-input field is a minor UX annoyance, but a wrong hardcoded URL makes the
connector non-functional in regional / self-hosted / sandbox deployments.

### Tier 1 — Hardcode the full URL
Use when ALL of these are true (no ambiguity):
- Docs show a specific, complete URL
- API is a public cloud SaaS with a single, well-known global endpoint
- No mention of self-hosted, on-premises, regional, or private cloud deployments
- No placeholder subdomains or variable host parts in the docs

```json
"apiEndpoint": "https://api.openai.com/v1/organization/audit_logs"
```

### Tier 2 — Named variable for the dynamic segment
Use when only a specific URL segment varies (tenant, account, org, region):
```json
"apiEndpoint": "https://{{oktaDomain}}/api/v1/logs"
"apiEndpoint": "https://api.github.com/enterprises/{{enterprise}}/audit-log"
```
Use a descriptive variable name (not `BaseUrl`) for just the dynamic part.

### Tier 3 — `{{BaseUrl}}` (the safe default)
Use when any of these are true, or when in doubt:
- Docs show relative paths (`GET /api/events`) without an explicit base URL
- Docs mention self-hosted, on-premises, or private cloud deployments
- Docs use a generic placeholder like `{baseUrl}` or `{your-instance-url}`
- Multiple possible hosts exist (production, sandbox, regional endpoints)

```json
"apiEndpoint": "{{BaseUrl}}/api/events"
```

### What goes into `{{BaseUrl}}`?

`{{BaseUrl}}` = scheme + host + optional port + shared path prefix. To determine the
boundary: collect all endpoint URLs for the connector, find their **longest common URL
prefix stopping at `/` boundaries**, and that common prefix is the BaseUrl. Everything
after the boundary goes in the hardcoded path portion of `apiEndpoint`.

| All endpoint URLs from docs                         | BaseUrl value                 | apiEndpoint                                     |
|-----------------------------------------------------|-------------------------------|-------------------------------------------------|
| `https://api.vendor.com/api/events`                 | `https://api.vendor.com`      | `{{BaseUrl}}/api/events`                        |
| `https://api.vendor.com/v2/events`, `.../v2/users`  | `https://api.vendor.com/v2`   | `{{BaseUrl}}/events`, `{{BaseUrl}}/users`       |
| `{baseUrl}/v0201/api/events`                        | `http://localhost:1337/v0201` | `{{BaseUrl}}/api/events`                        |
| `.../v1/users` AND `.../v2/events` (mixed versions) | `https://api.vendor.com`      | `{{BaseUrl}}/v1/users`, `{{BaseUrl}}/v2/events` |

The `{{BaseUrl}}` placeholder in the `instructionSteps` Textbox must use the SAME boundary
— include the shared version prefix (e.g. `https://api.openai.com/v1`, not
`https://api.openai.com`). See `ui-definitions.md`.

## Comprehensive Query Parameter Review

For every endpoint, walk EVERY query parameter in the API docs and decide how to configure
it. Skipping optional params produces a connector that ingests less data than the API
allows.

| Parameter category | How to configure | Example |
|--------------------|-------------------|---------|
| **Required identifiers** (resource IDs, scope selectors, tenant/org IDs) | `"{{variableName}}"` — user provides at runtime | `"accountId": "{{accountId}}"` |
| **Time filtering** (start/end times, "since") | Built-in time variables via `StartTimeAttributeName`/`EndTimeAttributeName` or `queryParametersTemplate` | See **Time Filtering** below |
| **Pagination** (page size, count, limit) | Static value — use API's maximum allowed | `"count": "100"` |
| **Event type/category filters** | Static value — broadest coverage (all types, all categories) | `"include": "all"` |
| **Output format** (response format, verbosity, fields) | Static value — prefer JSON, most verbose/complete | `"format": "json"` |
| **Optional enrichment** (extra context, related data) | Static value — include if it provides richer data for security analysis | `"details": "true"` |

Goal: maximum data coverage with correct API usage. Conservative omissions today become
missing telemetry tomorrow.

## queryWindowDelayInMin — when to set it

`queryWindowDelayInMin` delays polling to wait for data availability on the source side.
**Set this if** the docs mention any of:

| Trigger | Suggested delay |
|---------|-----------------|
| "Data may be delayed", general latency notes | 5-30 min |
| Eventual consistency / near real-time | 5-30 min |
| Analytics or aggregated views | 60-180 min |
| Batch / warehouse data | 120+ min |

Omit only for true real-time event streams. The default behaviour (no delay) silently
loses data when an API publishes events slightly after `TimeGenerated` would suggest.

## Rate-Limit Conversion

Convert the documented rate to QPS. Prefer the higher end of the allowed range —
conservative limits slow ingestion unnecessarily and don't protect against bursts (those
come from pagination, not baseline polling).

| Documented rate | Computed QPS | Recommended `rateLimitQPS` |
|-----------------|--------------|----------------------------|
| 5000 / hour     | ~1.4         | 10-50 (API allows it)      |
| 100 / minute    | ~1.7         | 10                         |
| 10 / second     | 10           | 10                         |
| No limit documented | —        | 10 (safe default)          |

## Request Configuration

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| **apiEndpoint** | Yes | string | — | URL to poll |
| **httpMethod** | No | string | `GET` | `GET` or `POST` |
| **queryWindowInMin** | No | integer/string | 5 | Poll interval AND time window (min). Minimum: 1. Can be a dynamic ARM expression for user-configurable intervals (see examples). |
| **isActive** | No | boolean | — | Explicitly enable/disable the connector. Production example: `"isActive": true` (Workday). |
| **rateLimitQPS** | No | integer | — | Max queries per second. The schema's canonical casing is `rateLimitQPS` (capital QPS). |
| **rateLimitConfig** | No | object | — | Advanced rate limit config using response headers |
| **retryCount** | No | integer (1-6) | 3 | Retries on failure |
| **timeoutInSeconds** | No | integer (1-180) | 20 | Request timeout |
| **queryTimeFormat** | No | string | ISO 8601 UTC | Date format. Constants: `UnixTimestamp`, `UnixTimestampInMills`. Or patterns: `yyyy-MM-dd`, `yyyy-MM-ddTHH:mm:ssZ`, etc. |
| **isPostPayloadJson** | No | boolean | false | POST body as JSON |
| **logResponseContent** | No | boolean | false | Diagnostic flag — when true, full response bodies are logged to Sentinel Health diagnostics for debugging. Leave `false` (or omit) for production; the logged content includes raw event data and may contain PII or credentials. |
| **headers** | No | object | — | Request headers. Many production connectors set `"User-Agent": "Scuba"` — this identifies traffic to the CCF infrastructure (see Scuba service tag in troubleshooting). |
| **queryParameters** | No | object | — | Query parameters |
| **StartTimeAttributeName** | No | string | — | Query param for start time. Can be used alone (without endTime) — the API will receive only a start-time filter. |
| **EndTimeAttributeName** | No | string | — | Query param for end time. Can be used alone or paired with startTime. |
| **QueryTimeIntervalAttributeName** | No | string | — | Combined time interval param |
| **QueryTimeIntervalPrepend** | Cond. | string | — | Prepend text for time interval (required if above set) |
| **QueryTimeIntervalDelimiter** | Cond. | string | — | Delimiter between start/end (required if above set) |
| **queryParametersTemplate** | No | string | — | Template for complex parameter scenarios |

## Built-in Variables

### For queryParameters
- `_now` — current timestamp in `queryTimeFormat` (resolves at request time)
- `{_QueryWindowStartTime}` — start of current query window
- `{_QueryWindowEndTime}` — end of current query window

### For queryParametersTemplate (additional)
- `{_APIKeyName}` — the configured API key name
- `{_APIKey}` — the configured API key value

## Request Examples

### Start/End Time Parameters
```json
"request": {
    "apiEndpoint": "https://api.example.com/events",
    "httpMethod": "GET",
    "queryTimeFormat": "yyyy-MM-ddTHH:mm:ssZ",
    "queryWindowInMin": 5,
    "StartTimeAttributeName": "since",
    "EndTimeAttributeName": "until",
    "retryCount": 3,
    "rateLimitQPS": 10,
    "timeoutInSeconds": 60,
    "headers": { "Accept": "application/json" }
}
```
Produces: `https://api.example.com/events?since={start}&until={end}`

### Time Interval Parameter
```json
"request": {
    "apiEndpoint": "https://api.example.com/events",
    "QueryTimeIntervalAttributeName": "filter",
    "QueryTimeIntervalPrepend": "timestamp gt ",
    "QueryTimeIntervalDelimiter": " and timestamp lt "
}
```
Produces: `?filter=timestamp gt {start} and timestamp lt {end}`

### Query Parameters with Built-in Variables
```json
"request": {
    "apiEndpoint": "https://api.example.com/events",
    "queryParameters": {
        "filter": "createdAt gt {_QueryWindowStartTime} and createdAt lt {_QueryWindowEndTime}"
    }
}
```

### POST with queryParametersTemplate
```json
"request": {
    "apiEndpoint": "https://api.example.com/query",
    "httpMethod": "POST",
    "isPostPayloadJson": true,
    "queryParametersTemplate": "{\"query\":\"SELECT * FROM events WHERE time BETWEEN '{_QueryWindowStartTime}' AND '{_QueryWindowEndTime}'\", '{_APIKeyName}': '{_APIKey}'}"
}
```

### Dynamic queryWindowInMin from UI Parameter (Workday)
```json
"request": {
    "apiEndpoint": "https://api.example.com/events",
    "queryWindowInMin": "[[int(parameters('queryWindow')[0])]",
    "httpMethod": "GET"
}
```
This lets users select their polling interval via a UI dropdown rather than hardcoding it.

### Start Time Without End Time (Box)
```json
"request": {
    "apiEndpoint": "https://api.box.com/2.0/events",
    "queryTimeFormat": "yyyy-MM-ddTHH:mm:ssZ",
    "StartTimeAttributeName": "created_after",
    "queryWindowInMin": 5
}
```
Produces: `?created_after={start}` — no end-time parameter. Useful when the API only supports a "since" filter.

### User-Agent Header Convention
```json
"request": {
    "headers": {
        "Accept": "application/json",
        "User-Agent": "Scuba"
    }
}
```
Many production connectors (Azure DevOps, Jira, Cisco Meraki) set `User-Agent` to `"Scuba"` or `"Scuba-Microsoft"`. This identifies traffic to the CCF infrastructure and may help with routing/diagnostics.

### Rate Limit Config with Response Headers
```json
"rateLimitConfig": {
    "evaluation": { "checkMode": "OnlyWhen429" },
    "extraction": {
        "source": "CustomHeaders",
        "headers": {
            "limit": { "name": "X-RateLimit-Limit", "format": "Integer" },
            "remaining": { "name": "X-RateLimit-Remaining", "format": "Integer" },
            "reset": { "name": "X-RateLimit-RetryAfter", "format": "UnixTimeSeconds" }
        }
    },
    "retryStrategy": { "useResetOrRetryAfterHeaders": true }
}
```

## Response Configuration

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| **eventsJsonPaths** | Yes | string[] | — | JSONPath to data. E.g., `["$"]` or `["$.value"]` |
| **format** | Yes | string | — | `json`, `csv`, `xml`, or `parquet` (parquet is supported but unusual for REST APIs — typically only seen with object-store-fronted endpoints) |
| **successStatusJsonPath** | No | string | — | JSONPath to success indicator |
| **successStatusValue** | No | string | — | Expected success value |
| **isGzipCompressed** | No | boolean | false | Response is gzip |
| **compressionAlgo** | No | string | — | `multi-gzip` or `deflate` |
| **csvDelimiter** | No | string | `,` | CSV field delimiter |
| **hasCsvBoundary** | No | boolean | false | CSV has boundary |
| **hasCsvHeader** | No | boolean | true | CSV has header row |
| **csvEscape** | No | string | `"` | CSV field escape character |
| **convertChildPropertiesToArray** | No | boolean | false | Convert object to array of events |

### Response Examples

#### JSON with nested data
```json
"response": {
    "eventsJsonPaths": ["$.value"],
    "format": "json",
    "successStatusJsonPath": "$.status",
    "successStatusValue": "success",
    "isGzipCompressed": true
}
```

#### CSV without header
```json
"response": {
    "eventsJsonPaths": ["$"],
    "format": "csv",
    "hasCsvHeader": false
}
```

## DCR Configuration (in RestApiPoller properties)

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| **dataCollectionEndpoint** | Yes | string | DCE URL |
| **dataCollectionRuleImmutableId** | Yes | string | DCR immutable ID |
| **streamName** | Yes | string | Must match `streamDeclarations` name (always `Custom-` prefix, even for ASIM destinations) |

```json
"dcrConfig": {
    "dataCollectionEndpoint": "[[parameters('dcrConfig').dataCollectionEndpoint]",
    "dataCollectionRuleImmutableId": "[[parameters('dcrConfig').dataCollectionRuleImmutableId]",
    "streamName": "Custom-MyStream"
}
```

Note: Use `[[parameters(` (double bracket) because these are evaluated at connect-time in a nested template.

### ASIM vs Custom Table outputStream Prefix

The `outputStream` in DCR `dataFlows` uses different prefixes depending on the destination:

| Destination | outputStream prefix | Example |
|-------------|-------------------|---------|
| Custom table (`_CL` suffix) | `Custom-` | `"outputStream": "Custom-MyTable_CL"` |
| ASIM standard table | `Microsoft-` | `"outputStream": "Microsoft-ASimNetworkSessionLogs"` |

Stream declarations (`streamDeclarations`) always use the `Custom-` prefix regardless of destination — even when the data ultimately flows to an ASIM table. The `Microsoft-` prefix only appears in `dataFlows[].outputStream`.

## Multiple Connections Pattern

A connector can have multiple named connections for different log types:

```json
// Connection 1 — Auth logs (high priority)
{
    "name": "[concat(parameters('workspace'),'/Microsoft.SecurityInsights/', 'AuthLogsConnector')]",
    "kind": "RestApiPoller",
    "properties": {
        "request": {
            "apiEndpoint": "[[concat('https://',parameters('domain'),'/api/v1/auth-logs')]",
            "queryWindowInMin": 1
        },
        "dcrConfig": { "streamName": "Custom-AuthLogs" }
    }
}

// Connection 2 — Activity logs (medium priority)
{
    "name": "[concat(parameters('workspace'),'/Microsoft.SecurityInsights/', 'ActivityLogsConnector')]",
    "kind": "RestApiPoller",
    "properties": {
        "request": {
            "apiEndpoint": "[[concat('https://',parameters('domain'),'/api/v1/activity-logs')]",
            "queryWindowInMin": 5
        },
        "dcrConfig": { "streamName": "Custom-ActivityLogs" }
    }
}
```

Each connection can have its own:
- API endpoint and query parameters
- Polling interval (`queryWindowInMin`)
- Stream name (routing to different DCR dataFlows)
- Authentication (typically shared)
- Pagination config

## Nested Steps / Multi-step Data Enrichment (Advanced)

Some connectors need to chain multiple API calls — fetching primary data, then enriching each record with details from secondary endpoints. The CCF supports this via the `shouldJoinNestedData` / `stepCollectorConfigs` pattern.

### How It Works

1. **Root collector** fetches primary data (e.g., list of cases)
2. For each record, a KQL expression extracts placeholder values (e.g., `dataSourceName`)
3. A **nested step** uses those placeholders (`$dataSourceName$`) to call a secondary endpoint
4. Steps can be chained further — each step can itself define `nextSteps`
5. Results from all steps are joined together before ingestion

### Properties

| Field | Level | Type | Description |
|-------|-------|------|-------------|
| `shouldJoinNestedData` | connector | boolean | Enable nested data enrichment |
| `joinedDataStepName` | connector | string | Label for the joined data from this step |
| `stepInfo` | connector | object | Defines the nesting relationship |
| `stepInfo.stepType` | — | string | `"Nested"` for chained steps |
| `stepInfo.nextSteps` | — | array | Array of next-step definitions |
| `stepInfo.nextSteps[].stepId` | — | string | References a key in `stepCollectorConfigs` |
| `stepInfo.nextSteps[].stepPlaceholdersParsingKql` | — | string | KQL that extracts placeholder values from the current step's data |
| `stepCollectorConfigs` | connector | object | Dictionary of step configs keyed by `stepId` |
| `extra.nestedTransformName` | connector | string | Transform for flattening nested data (e.g., `/ASI/Microsoft/MvExpandTransformer`) |

### Placeholder Syntax in Nested Steps

The KQL in `stepPlaceholdersParsingKql` extracts named fields. Those field names become placeholders in the next step's request URL and query parameters, wrapped in `$...$`:

```
// KQL extracts dataSourceName and policyName:
"source | project res = parse_json(data) | project dataSourceName = res.dataSourceName, policyName = res.policyName"

// Next step uses them in apiEndpoint:
"apiEndpoint": "https://{{bigidFqdn}}/api/v1/ds_connections/$dataSourceName$"

// And in queryParameters:
"filter": "SYSTEM = \"$dataSourceName$\" AND policy IN (\"$policyName$\")"
```

### Example (BigID — 3-step enrichment chain)

```json
{
    "kind": "RestApiPoller",
    "properties": {
        // ... auth, dcrConfig ...
        "request": {
            "apiEndpoint": "https://{{bigidFqdn}}/api/v1/actionable-insights/all-cases",
            "httpMethod": "GET"
        },
        "response": { "eventsJsonPaths": ["$.data.cases"], "format": "json" },
        "paging": { "pagingType": "Offset", "pageSize": 50, "pageSizeParameterName": "limit", "offsetParaName": "offset" },

        // Step 1: Enable nested enrichment
        "shouldJoinNestedData": true,
        "joinedDataStepName": "dspmCase",
        "stepInfo": {
            "stepType": "Nested",
            "nextSteps": [{
                "stepId": "fetchDataSourceDetails",
                "stepPlaceholdersParsingKql": "source | project res = parse_json(data) | project dataSourceName = res.dataSourceName, policyName = res.policyName"
            }]
        },

        // Step configs for chained calls
        "stepCollectorConfigs": {
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
                    "apiEndpoint": "https://{{bigidFqdn}}/api/v1/ds_connections/$dataSourceName$"
                },
                "response": { "eventsJsonPaths": ["$.ds_connection"], "format": "json" }
            },
            "fetchObjectsDetails": {
                "shouldJoinNestedData": true,
                "joinedDataStepName": "expand",
                "request": {
                    "httpMethod": "GET",
                    "apiEndpoint": "https://{{bigidFqdn}}/api/v1/data-catalog/",
                    "queryParameters": {
                        "filter": "SYSTEM = \"$dataSourceName$\" AND policy IN (\"$policyName$\")"
                    }
                },
                "response": { "eventsJsonPaths": ["$.results"], "format": "json" }
            }
        },
        "extra": { "nestedTransformName": "/ASI/Microsoft/MvExpandTransformer" }
    }
}
```

This is an advanced pattern — most connectors don't need it. Use it when the API requires multiple sequential calls to build a complete event record.
