Scripts for building, packaging, and validating Microsoft Sentinel CCF (Codeless Connector Framework) solutions. Most are from the official [Azure-Sentinel](https://github.com/Azure/Azure-Sentinel) `Tools/Create-Azure-Sentinel-Solution/` pipeline; `validate_connector.py` is a custom validator for single-file ARM templates.

## Custom Script

### `validate_connector.py`
Automated validation of a single-file CCF ARM template (`mainTemplate.json`) against the deployment checklist. Checks resource count, bracket escaping, stream declarations, table names, KQL transforms, securestring usage, pagination, rate limits, and cross-resource consistency (poller<->definition, poller<->DCR stream, DCR outputStream<->table). Run after every template change:
```bash
python scripts/validate_connector.py mainTemplate.json --verbose
python scripts/validate_connector.py mainTemplate.json --connector-type push
```
Exits 0 on pass (warnings OK), 1 on any hard failure. Warnings (e.g. unconventional TimeGenerated passthrough) are displayed but don't block.

## Microsoft Packaging Pipeline (`V3/`, `common/`)

These scripts power the `createSolutionV3.ps1` pipeline that packages separate-file connectors into a single `mainTemplate.json` for Content Hub submission. They contain validation logic worth studying but are not directly runnable against our single-file ARM templates.

### `V3/createSolutionV3.ps1`
Entry point for the packaging pipeline. Parses parameters, resolves solution paths, validates folder structure and version format, loads the solution data file, and orchestrates the full build.

### `common/createCCPConnector.ps1`
Core CCF resource processor. Reads building block files (definition, poller, DCR, table), validates cross-file relationships, generates ARM resources with correct escaping and dependency chains. Key validation logic:
- **Auth type validation**: Enforces valid `auth.type` per connector kind (OAuth2, Basic, APIKey, JwtToken for RestApiPoller; Oracle for OCI)
- **Required property checks**: `connectorDefinitionName`, `dataType`, `dcrConfig`, `dcrConfig.streamName`, `auth`, `request`  -- exits with error if missing
- **Auth-specific required fields**: OAuth2 requires `ClientId` + `ClientSecret`; Basic requires `UserName` + `Password`; APIKey requires `ApiKey`; JwtToken requires either `userName.value` + `password.value` or `UserToken`, plus `TokenEndpoint`
- **Connector kind validation**: Must be one of `RestApiPoller`, `WebSocket`, `GCP`, `AmazonWebServicesS3`, `Push`, `StorageAccountBlobContainer`, `OCI`, `PurviewAudit`
- **Placeholder-to-parameter conversion**: Transforms `{{placeholder}}` syntax into `[[parameters('placeholder')]` ARM expressions
- **DCR processing**: Ensures `logAnalytics` destination exists with `workspaceResourceId`, adds `dataCollectionEndpointId` if missing
- **Instruction step parameter extraction**: Walks `instructionSteps` to derive connection template parameters (Textbox -> securestring, OAuthForm -> ClientId/ClientSecret/AuthorizationCode, Dropdown -> array, ContextPane -> recursive)
- **Nested step validation**: For BigID-style multi-step enrichment, validates `stepInfo.nextSteps` and `stepCollectorConfigs` contain matching `stepId` references

### `common/get-ccp-details.ps1`
Discovers and maps relationships between CCF building block files (definition <-> poller <-> DCR <-> table). Validates that `connectorDefinitionName` matches `connectorUiConfig.id`, poller `streamName` matches DCR `dataFlows.streams[]`, and DCR `outputStream` maps to table name. Known bugs (as of Feb 2026):
- Missing `$counter++` in multi-poller array loop (~line 152-201)  -- only captures last poller
- Line 297 uses input stream name (`$dataFlowStreamName`) instead of output stream (`$dataFlowOutputStreamName`) for table matching

### `common/standardLogStreams.ps1`
Hashtable of 208+ stream-name -> standard-table mappings (e.g. `Custom-CiscoMeraki_API` -> standard ASIM tables). Provides `GetKeyValue()` lookup. Useful for validating that `Microsoft-` prefixed `outputStream` values reference real standard tables.

### `common/commonFunctions.ps1`
Shared utilities: JSON file loading with error handling, empty property cleanup, global counter initialization for content items (analytics rules, connectors, workbooks, etc.).

### `common/summaryRules.ps1`
Summary rule YAML processor. Validates 8 required properties (`id`, `displayName`, `description`, `requiredDataConnectors`, `destinationTable`, `query`, `binSize`, `version`) with early-exit on failure. Good pattern for strict required-property validation.

### `common/storageAccountDeploymentTemplate.ps1`
Generates ARM resources for StorageAccountBlobContainer connectors (storage queues, Event Grid topics, role assignments). Only relevant for blob-triggered data collection.

## ARM Template Test Toolkit (`arm-ttk/`)

### `arm-ttk/download-arm-ttk.ps1`
Downloads Microsoft's official ARM Template Test Toolkit from GitHub. Prerequisite for marketplace certification testing.

### `arm-ttk/run-arm-ttk-in-automation.ps1`
Runs `Test-AzTemplate` against solution packages. Filters results, reports errors, exits non-zero on failure. Used in CI/CD for Content Hub submission compliance.

## Templating Utilities (`common/templating/`)

### `common/templating/baseMainTemplate.json` / `baseCreateUiDefinition.json`
Skeleton JSON templates used as starting points by the packaging pipeline.

### `common/templating/replaceLocationValue.js` / `replacePlaybookParamNames.js` / `replacePlaybookVarNames.js`
Node.js string replacement utilities for playbook parameter/variable renaming during packaging. Not relevant to CCF connectors.

## Examples (`examples/`)

### `examples/Solution_ExampleInput.json` / `SolutionMetadata_ExampleTemplate.json`
Sample data input files showing the expected format for the `createSolutionV3.ps1` pipeline.
