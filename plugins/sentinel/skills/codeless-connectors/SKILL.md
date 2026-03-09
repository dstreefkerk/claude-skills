---
name: codeless-connectors
description: "Use BEFORE writing any Microsoft Sentinel connector ARM template, DCR, KQL transform, or createUiDefinition.json. Provides the complete CCF (Codeless Connector Framework) reference for RestApiPoller, Push, and GCP connector types  -- including escaping rules, authentication, pagination, UI definitions, and deployment gotchas. Also use when debugging connector deployment failures or reviewing existing CCP templates."
---

# Microsoft Sentinel Codeless Connector Framework (CCF) Expert

## Success Criteria
1. ARM template contains all 5 required resources with correct dependency chain (contentPackages first, all others dependsOn it).
2. Every ARM expression uses the correct bracket escaping: single `[` in parent and DataConnector (deploy-time) templates, double `[[` in ResourcesDataConnector (connect-time) templates. `/metadata` resources always use `[[`.
3. Stream declarations match the raw incoming API data shape  -- not the transformed output.
4. The deployment checklist at the bottom of this file is fully addressed before presenting output.
5. ConnectorDefinition contentTemplate depends only on contentPackages, custom tables exist as top-level ARM resources, and Connections contentProductId uses the `'rdc'` prefix.

You are an expert on building data connectors for Microsoft Sentinel using the Codeless Connector Framework (CCF). This was formerly called the Codeless Connector Platform (CCP). Use only the current framework - never reference the legacy/v1 CCP.

## Reference Files

Detailed references are in sibling files - read them as needed:
- `references/arm-template-structure.md`  -- ARM template resources, escaping, variables
- `references/authentication-types.md`  -- Basic, APIKey, OAuth2, JWT configurations
- `references/pagination-types.md`  -- All paging types and properties
- `references/kql-transforms.md`  -- Complete supported/blocked KQL function list
- `references/push-connectors.md`  -- CCF Push connector specifics (preview)
- `references/ui-definitions.md`  -- Data connector UI instruction types
- `references/request-response-config.md`  -- Request, response, and DCR config properties
- `references/troubleshooting.md`  -- Deployment errors, health monitoring, debugging
- `references/connector-builder.md`  -- Step-by-step builder workflow for creating connectors from scratch (all 4 destination types)
- `references/asim-schemas.md`  -- ASIM normalization schema reference for all 10 supported event types
- `references/create-ui-definition.md`  -- createUiDefinition.json builder guide for Azure Portal deployment UI
- `references/production-examples.md`  -- Annotated excerpts from production connectors (Cisco Meraki, 1Password, Auth0, Azure DevOps, Box, Jira, Proofpoint TAP, BigID)
- `scripts/validate_connector.py`  -- Automated validation script for ARM templates (run after every template generation)
- `scripts/test-ccp-mapping.ps1`  -- Tests Definition->Poller->DCR->Table mapping via get-ccp-details.ps1 (run against extracted separate files)
- `references/packaging.md`  -- Solution packaging with createSolutionV3.ps1, building block file structure, naming conventions
- `references/ccf-packaging-details.md`  -- CCF packaging: folder naming, file suffixes, cross-file mapping, multi-poller patterns, connector kind specifics
- `scripts/README.md`  -- Packaging scripts guide: prerequisites, running createSolutionV3.ps1, data input format, script architecture

## Architecture Overview

### Connector Kinds

The CCF has more connector kinds than commonly documented. The three most frequently built are `RestApiPoller`, `Push`, and `GCP`, but the repo contains several additional specialised kinds:

| Kind | Model | Status | Example |
|------|-------|--------|---------|
| `RestApiPoller` | Sentinel polls a REST API on a schedule | GA | Most modern connectors |
| `Push` | App pushes data via Logs Ingestion API | Public Preview (Feb 2026) | -- |
| `GCP` | Pre-configured for Google Cloud Platform | GA | Google Cloud solutions |
| `AmazonWebServicesS3` | Reads from an AWS S3 bucket | GA | AWS WAF, AWS Network Firewall |
| `WebSocket` | Connects to a WebSocket stream | GA | Proofpoint POD Email Security |
| `OCI` | Oracle Cloud Infrastructure log stream | GA | Oracle Cloud Infrastructure |
| `PurviewAudit` | Microsoft Purview audit log stream | GA | Microsoft Copilot, Business Applications |
| `StorageAccountBlobContainer` | Event-driven ingest from Azure Blob Storage via Event Grid + Storage Queue | Public Preview (Feb 2026) | `DataConnectors/Templates/Connector_StorageBlob_CCF_template.json` |

**Note:** When writing about CCF connector kinds, do not claim RestApiPoller/Push/GCP are the only three -- the list above was verified against the Azure/Azure-Sentinel repo (Feb 2026). Always use "a new connector kind" not "the Nth connector kind" unless you have verified the current count.

### Legacy Format: APIPolling (v1)

Older connectors in `DataConnectors/` use `kind: "APIPolling"`  -- the v1 format. Key differences from v2 (`RestApiPoller`):
- Resource type: `Microsoft.OperationalInsights/workspaces/providers/dataConnectors` (not `Microsoft.SecurityInsights/dataConnectors`)
- Auth field: `auth.authType` (not `auth.type`)
- Config: `pollingConfig` + `connectorUiConfig` inline in one resource (no separate definition/poller files)
- No DCR  -- data goes directly to a custom table
- Connectivity criteria: `"type": "SentinelKindsV2"` (not `"HasDataConnectors"`)

**Always use RestApiPoller (v2) for new connectors.** The v1 format is documented here only for reference when reading legacy connectors (e.g., Proofpoint TAP, the original Atlassian Jira in `DataConnectors/`).

### Pull Connector Data Flow
1. Poller sends HTTP request to source API (per `queryWindowInMin`)
2. Raw JSON/CSV/XML response received
3. Stream declaration describes the raw incoming shape
4. DCR `transformKql` transforms the data
5. Output written to destination table(s) in Log Analytics

### Push Connector Data Flow
1. Deploy connector in Sentinel (creates Entra app, DCR, DCE, table, role assignments)
2. User receives connection details (tenant ID, app ID, secret, DCE URI, DCR ID, stream name)
3. App authenticates via OAuth 2.0 client_credentials, POSTs JSON to DCE
4. DCR transforms data (optional), writes to destination table

## ARM Template Structure (Pull Connectors)

### Five Required Resources (in dependency order)
1. **contentPackages**  -- solution package container (deploy first)
2. **contentTemplates #1**  -- houses DCR, custom table, and metadata
3. **dataConnectorDefinitions**  -- connector UI configuration (`kind: "Customizable"`)
4. **metadata**  -- links everything together
5. **contentTemplates #2**  -- houses RestApiPoller connection rules

Every resource must `dependsOn` the contentPackage. See `references/arm-template-structure.md`.

### Critical Escaping Rules

There are TWO types of nested templates (`contentTemplates`), and each has different escaping:

| Where the expression is | contentKind | Bracket syntax |
|------------------------|-------------|----------------|
| Parent template (deploy-time) | n/a | `"[parameters('x')]"` |
| Deploy-time nested template (DCR, table, metadata) | `DataConnector` | `"[parameters('x')]"` |
| Connect-time nested template (poller, connections) | `ResourcesDataConnector` | `"[[parameters('x')]"` |
| CCP UI-collected parameter in connector props | (inside ResourcesDataConnector) | `"[[parameters('x')]"` |

**Exception:** `/metadata` resources inside ANY nested template use `[[` for deferred content-hub evaluation, regardless of the template's contentKind.

`[[` tells ARM: "don't evaluate now -- store as literal for later." The closing bracket is NOT doubled. In connect-time (`ResourcesDataConnector`) templates, this applies to ALL ARM functions: `concat()`, `resourceId()`, `subscription()`, `resourceGroup()`, etc.

**Common mistake:** Using `[[` in a `DataConnector` template causes ARM to store the literal string (e.g. `"[parameters('location')]"`) instead of evaluating it, leading to errors like `InvalidResourceLocation`.

### Variable Scoping
Variables defined in the parent template are NOT accessible inside nested `mainTemplate` blocks. Define shared config within the nested template's own `variables` section or pass as parameters.

### Solution Version
`_solutionVersion` must be `"3.0.0"` or above for CCF templates.

## Data Collection Rules (DCRs)

### Key Rules
- **One DCR per connector**  -- can contain multiple dataFlows routing to different tables
- DCR must share region with DCE
- Custom table names require `_CL` suffix
- Stream names in `streamDeclarations` must start with `Custom-` prefix (even for ASIM destinations)
- `outputStream` prefix depends on destination: `Custom-` for custom tables, `Microsoft-` for ASIM standard tables (e.g., `Microsoft-ASimNetworkSessionLogs`)

### Stream Declarations
Describe the **raw incoming data** shape  -- NOT the transformed output. If the API returns `ts`, `eventType`, `srcIp`, declare those names/types. Fields created by `transformKql` (like `TimeGenerated`) do NOT go in stream declarations.

### dataFlows
Each dataFlow specifies: input streams, destinations, `transformKql`, and `outputStream`. Multiple dataFlows enable routing different event types to different tables from a single stream.

### transformKql
- `"source"` for pass-through (no transformation)
- Must produce a `TimeGenerated` column (datetime)
- Transforms taking >20 seconds may cause data loss  -- keep under 1 second
- No blank lines in KQL strings
- Escape quotes in JSON: `\"` inside the transformKql string
- See `references/kql-transforms.md` for the complete supported function list

### KQL Transform Quick Reference (Critical Items)

**Supported:** `where`, `extend`, `project`, `project-away`, `project-rename`, `parse` (max 10 cols), `let`, `datatable`, `print`, `columnifexists`  -- Note: `let` and `datatable` were added in newer DCR API versions (2023+). Older references may list them as unsupported.

**NOT supported:** `summarize`, `join`, `union`, `mv-expand`, `mv-apply`, `top`, `sort`, `distinct`, `project-reorder`, `parse_csv`, `invoke`, `scan`, `partition`

**Blocked functions:** `coalesce` (use `iif(isnotnull(a),a,b)`), `replace_string`, `replace_regex`, `bag_keys`, `bag_values`, `bag_set`, `bag_remove_keys`, `dynamic()` literals (use `parse_json()`)

**Supported:** `has`, `has_cs`, `!has`, `contains`, `startswith`, `endswith`, `matches regex`, `in`, `!in`

**Special functions:** `geo_location` (adds latency), `parse_cef_dictionary`

## RestApiPoller Configuration

### Authentication Types
| Type | Use When |
|------|----------|
| `Basic` | Username + password |
| `APIKey` | API key in header or POST body |
| `OAuth2` | `authorization_code` or `client_credentials` grant |
| `JwtToken` | JWT token via username/password endpoint |

OAuth2 does NOT support client certificate credentials. See `references/authentication-types.md`.

### Pagination Types
| Type | Use When |
|------|----------|
| `LinkHeader` | Next/prev page URLs in headers or body |
| `PersistentLinkHeader` | Same as LinkHeader but persists cursor across query windows |
| `NextPageUrl` | Full next-page URL in response body |
| `NextPageToken` | Token/cursor for next page |
| `PersistentToken` | Token persists server-side across requests |
| `Offset` | Skip/offset parameter |
| `CountBasedPaging` | Page number parameter |

`PersistentLinkHeader` only allows one concurrent query to avoid race conditions. See `references/pagination-types.md`.

### Key Request Properties
| Property | Description | Default |
|----------|-------------|---------|
| `apiEndpoint` | URL to poll (required) |  -- |
| `httpMethod` | GET or POST | GET |
| `queryWindowInMin` | Poll interval AND time window (min) | 5 |
| `rateLimitQPS` | Max queries per second (integer) |  -- |
| `retryCount` | Retries on failure (1-6) | 3 |
| `timeoutInSeconds` | Request timeout (1-180) | 20 |
| `queryTimeFormat` | Date format for time params | ISO 8601 UTC |
| `startTimeAttributeName` | Query param for start time |  -- |
| `endTimeAttributeName` | Query param for end time |  -- |
| `isPostPayloadJson` | POST body as JSON | false |

Built-in variables for `queryParameters`: `{_QueryWindowStartTime}`, `{_QueryWindowEndTime}`
Additional for `queryParametersTemplate`: `{_APIKeyName}`, `{_APIKey}`

### Key Response Properties
| Property | Description |
|----------|-------------|
| `eventsJsonPaths` | JSONPath to data in response (required), e.g. `["$"]` or `["$.value"]` |
| `format` | `json`, `csv`, or `xml` (required) |
| `isGzipCompressed` | Response is gzip compressed |
| `successStatusJsonPath` | JSONPath to success indicator |
| `convertChildPropertiesToArray` | When API returns object instead of array |

## Connector UI Definition

### Key Properties
- `kind` must be `"Customizable"`
- `connectivityCriteria.type`: use `"HasDataConnectors"` for pull, `"IsConnectedQuery"` for push
- `graphQueriesTableName`: set to your actual table name (enables sample queries)

### Instruction Types
| Type | Purpose |
|------|---------|
| `Textbox` | Text input (text, password, number, email) |
| `OAuthForm` | OAuth-style credential input (works for API key + secret too) |
| `ConnectionToggleButton` | Connect/disconnect button (triggers DCR deployment) |
| `CopyableLabel` | Read-only copyable text (supports `fillWith` for auto-populated values) |
| `InfoMessage` | Informational text (inline or block) |
| `Markdown` | Markdown-formatted text |
| `Dropdown` | Selection dropdown |
| `ContextPane` | Side panel with additional inputs |
| `DataConnectorsGrid` | Grid display of connections |
| `DeployPushConnectorButton` | Push connector deployment trigger |
| `InstructionStepsGroup` | Collapsible instruction group |
| `InstallAgent` | Links to agent installation |

See `references/ui-definitions.md` for full property details.

## Multiple Connections Per Connector

A single connector definition can have multiple RestApiPoller connections with different:
- API endpoints and query parameters
- Polling intervals (`queryWindowInMin`)
- Stream names (routing to different DCR dataFlows/tables)

Pattern: Create separate named connections for each log source (e.g., auth logs at 1 min, activity logs at 5 min, config logs at 15 min).

## Critical Gotchas

### ARM Template
1. **Bracket escaping depends on contentKind** -- `DataConnector` (deploy-time) templates use single `[`, `ResourcesDataConnector` (connect-time) templates use double `[[`. Using `[[` in a DataConnector template causes literal strings instead of evaluated values (e.g. `InvalidResourceLocation`). Exception: `/metadata` resources always use `[[`.
2. **Variables from parent template are not accessible** in nested `mainTemplate` blocks
3. **Delete all resources before redeploying**  -- DCR, custom table, connector definitions, content packages
4. **DCR `workspaceResourceId`** uses single brackets (it's in a DataConnector template, evaluated at deploy time), but `dcrConfig` properties use double brackets (they're in a ResourcesDataConnector template, evaluated at connect time)
5. **ConnectorDefinition contentTemplate must NOT dependsOn the Connections contentTemplate** -- only depend on contentPackages. A reversed dependency causes "content template $XxxDefinition not found" at Connect time.
6. **Custom tables must be top-level resources** in addition to being inside the contentTemplate mainTemplate. Without them, the Connect button fails with InvalidOutputTable.
7. **Table resources inside contentTemplate mainTemplate must not have `kind` or `location`** -- omit both properties.
8. **Connections contentProductId must use `'rdc'` prefix** (not `'dc'`). Use `'sl'` for Solution, `'dc'` for DataConnector, `'rdc'` for ResourcesDataConnector.
9. **Connections metadata parentId must reference an existing resource** -- for multi-poller connectors, point to the dataConnectorDefinition since there's no single poller resource to reference.

### KQL Transforms
5. **`dynamic()` literal syntax is blocked**  -- use `parse_json('{"key":"val"}')`
6. **`coalesce()` is blocked**  -- use `iif(isnotnull(a), a, b)`
7. **`replace_string` and `replace_regex` are blocked**  -- use `extract` with regex or `parse`
8. **`parse` limited to 10 columns** per statement  -- chain multiple `parse` statements
9. **`bag_keys`, `bag_values`, `bag_set`, `bag_remove_keys` are all blocked**
10. **No blank lines in transformKql**  -- causes parsing errors

### Polling & Rate Limits
11. **Rate limit issues come from pagination bursts**, not baseline polling  -- 10 pages at once triggers 429s even if polling is infrequent
12. **`queryParametersTemplate` is for connection validation only**  -- also define `queryParameters` for ongoing polling
13. **There is no separate time window for connection validation**  -- `queryWindowInMin` applies globally

### Deployment
14. **Data ingestion can take up to 30 minutes** after connecting
15. **If "Connect" button hangs**: test API manually, check Azure IP blocking, verify Sentinel health diagnostics
16. **Network isolation**: allowlist CCP IPs using the **Scuba** Azure service tag
17. **`securestring`** for all credentials  -- values unreadable after deployment
18. **Table names in content templates must NOT include workspace prefix**  -- the Portal adds workspace scoping automatically; compound names like `workspace/Table_CL` cause 404 from double-nesting (`/workspaces/{ws}/tables/{ws}/Table_CL`)

## Deployment Checklist

- [ ] Custom table has `_CL` suffix and correct schema
- [ ] Stream declarations match raw incoming data shape (not transformed output)
- [ ] `transformKql` uses only supported KQL subset
- [ ] `TimeGenerated` produced by every transformation
- [ ] ARM escaping correct: single `[` in DataConnector templates, double `[[` in ResourcesDataConnector templates (except `/metadata` resources which always use `[[`)
- [ ] `securestring` for all credentials
- [ ] DCE in same region as DCR
- [ ] `rateLimitQPS` and `retryCount` set for source API limits
- [ ] Page size maximized to reduce pagination calls
- [ ] Polling intervals staggered across connections
- [ ] `connectivityCriteria` type is `HasDataConnectors` (pull) or `IsConnectedQuery` (push)
- [ ] Connector `kind` is `Customizable`
- [ ] Solution version is 3.0.0+
- [ ] No blank lines in KQL transformation strings
- [ ] `contentPackages` resource has `contentProductId` and `packageId` properties
- [ ] Previous deployment resources cleaned up before redeploying
- [ ] ConnectorDefinition contentTemplate depends only on contentPackages (not Connections template)
- [ ] Custom tables exist as top-level ARM resources (not just inside contentTemplate)
- [ ] Table resources in nested template have no `kind` or `location` properties
- [ ] Connections contentProductId uses `'rdc'` prefix
- [ ] Connections metadata parentId references an existing resource

## Key Microsoft Docs References
- Create pull connector: https://learn.microsoft.com/en-us/azure/sentinel/create-codeless-connector
- Create push connector: https://learn.microsoft.com/en-us/azure/sentinel/create-push-codeless-connector
- Connection rules reference: https://learn.microsoft.com/en-us/azure/sentinel/data-connector-connection-rules-reference
- UI definitions reference: https://learn.microsoft.com/en-us/azure/sentinel/data-connector-ui-definitions-reference
- KQL transforms reference: https://learn.microsoft.com/en-us/azure/azure-monitor/essentials/data-collection-transformations-kql
- DCR structure: https://learn.microsoft.com/en-us/azure/azure-monitor/essentials/data-collection-rule-structure

## Example Connectors on GitHub

**RestApiPoller (v2)  -- in `Solutions/`:**
- **Cisco Meraki**  -- Multi-connection, LinkHeader pagination, ASIM multi-table transforms (`Solutions/Cisco Meraki Events via REST API/`)
- **1Password**  -- Multi-endpoint POST, NextPageToken, shared stream (`Solutions/1Password/`)
- **Auth0**  -- OAuth2 client_credentials, PersistentToken (`Solutions/Auth0/`)
- **Azure DevOps**  -- OAuth2 authorization_code, NextPageToken (`Solutions/AzureDevOpsAuditing/`)
- **Box**  -- OAuth2 with custom tokenEndpointQueryParameters (`Solutions/Box/`)
- **BigID**  -- Nested steps / multi-step enrichment (advanced) (`Solutions/BigID/`)
- **Atlassian Jira (v2)**  -- Basic auth, Offset pagination (`Solutions/AtlassianJiraAudit/`)
- Ermes Browser Security, Palo Alto Prisma Cloud CWPP, Sophos Endpoint Protection, Workday, Okta SSO

**Legacy APIPolling (v1)  -- in `DataConnectors/`:**
- Atlassian Jira (original), Proofpoint TAP

All at: https://github.com/Azure/Azure-Sentinel/tree/master/
See `references/production-examples.md` for annotated excerpts from these connectors.

## Automated Validation

After generating any ARM template, run the validator script:

```bash
python scripts/validate_connector.py mainTemplate.json --verbose
```

The script runs 48 checks covering: resource count, bracket escaping, stream declarations, table names, KQL transforms, securestring usage, pagination, content template dependencies, contentProductId prefixes, nested table constraints, top-level table existence, and more. It exits with code 1 if any check fails.

For push connectors, add `--connector-type push` to adjust the connectivityCriteria check.

The script lives at: `scripts/validate_connector.py` (relative to this skill's directory).

## Self-Verification
Before presenting any ARM template, connector config, or KQL transform to the user:
1. Run `scripts/validate_connector.py` on the generated template and fix any failures.
2. Verify all Success Criteria (top of this file) are met.
3. Walk through the Deployment Checklist above.
4. **Test API query parameters live** -- Run a test API call to verify parameter names work correctly. APIs vary widely in format: `__gte` vs `[gte]`, `created_at` vs `timestamp`, date formats, etc. Don't assume based on examples -- test against the actual API.
5. If any criterion fails, revise and re-check (up to 5 iterations) before presenting output.
