# Request, Response, and DCR Configuration Reference

## Request Configuration

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| **apiEndpoint** | Yes | string | — | URL to poll |
| **httpMethod** | No | string | `GET` | `GET` or `POST` |
| **queryWindowInMin** | No | integer/string | 5 | Poll interval AND time window (min). Minimum: 1. Can be a dynamic ARM expression for user-configurable intervals (see examples). |
| **isActive** | No | boolean | — | Explicitly enable/disable the connector. Production example: `"isActive": true` (Workday). |
| **rateLimitQPS** | No | integer | — | Max queries per second. Note: both `rateLimitQPS` and `rateLimitQps` are accepted (casing varies across production connectors). |
| **rateLimitConfig** | No | object | — | Advanced rate limit config using response headers |
| **retryCount** | No | integer (1-6) | 3 | Retries on failure |
| **timeoutInSeconds** | No | integer (1-180) | 20 | Request timeout |
| **queryTimeFormat** | No | string | ISO 8601 UTC | Date format. Constants: `UnixTimestamp`, `UnixTimestampInMills`. Or patterns: `yyyy-MM-dd`, `yyyy-MM-ddTHH:mm:ssZ`, etc. |
| **isPostPayloadJson** | No | boolean | false | POST body as JSON |
| **headers** | No | object | — | Request headers. Many production connectors set `"User-Agent": "Scuba"` — this identifies traffic to the CCF infrastructure (see Scuba service tag in troubleshooting). |
| **queryParameters** | No | object | — | Query parameters |
| **startTimeAttributeName** | No | string | — | Query param for start time. Can be used alone (without endTime) — the API will receive only a start-time filter. |
| **endTimeAttributeName** | No | string | — | Query param for end time. Can be used alone or paired with startTime. |
| **queryTimeIntervalAttributeName** | No | string | — | Combined time interval param |
| **queryTimeIntervalPrepend** | Cond. | string | — | Prepend text for time interval (required if above set) |
| **queryTimeIntervalDelimiter** | Cond. | string | — | Delimiter between start/end (required if above set) |
| **queryParametersTemplate** | No | string | — | Template for complex parameter scenarios |

## Built-in Variables

### For queryParameters
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
    "startTimeAttributeName": "since",
    "endTimeAttributeName": "until",
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
    "queryTimeIntervalAttributeName": "filter",
    "queryTimeIntervalPrepend": "timestamp gt ",
    "queryTimeIntervalDelimiter": " and timestamp lt "
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
    "startTimeAttributeName": "created_after",
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
| **format** | Yes | string | — | `json`, `csv`, or `xml` |
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
        "paging": { "pagingType": "Offset", "PageSize": 50, "PageSizeParameterName": "limit", "OffsetParaName": "offset" },

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
