# Troubleshooting & Deployment Reference

## Deployment Strategy

### Incremental Testing (Recommended Order)
1. Deploy custom table schema first — verify in portal
2. Deploy DCR separately — verify it appears in portal
3. Test KQL transforms in Log Analytics with real `datatable` sample data
4. Deploy the full ARM template
5. Connect and verify data flow
6. Wait up to 30 minutes for initial data ingestion

### Delete Before Redeploying
Microsoft recommends deleting these before redeploying:
- Data Collection Rule (DCR)
- Custom table
- Data connector definitions
- Content packages

Otherwise you'll get confusing conflicts between old and new resources.

### CLI Deployment with Debug
```bash
az deployment group create \
    --resource-group <rg> \
    --template-file template.json \
    --debug
```
Portal deployments often hide useful error details. Use `--debug` for full error output.

### ARM Template Validation
Use the ARM template test toolkit (arm-ttk):
```powershell
# Install arm-ttk
Import-Module ./arm-ttk/arm-ttk.psd1

# Test template
Test-AzTemplate -TemplatePath ./template.json
```
Note: arm-ttk failures are **expected and normal** for CCF Push connectors.

## Common Errors

### "Property id is invalid"
```
LinkedInvalidPropertyId: Property id '[variables('workspaceResourceId')]' at path
'properties.destinations.logAnalytics[0].workspaceResourceId' is invalid
```
**Cause:** ARM expression not evaluated because it's in a nested template with wrong escaping, or the variable isn't in scope.
**Fix:** Ensure `workspaceResourceId` is fully qualified and use correct escaping for the nesting level.

### "Package cannot be found"
**Cause:** Missing `dependsOn` chain. ARM deployed resources out of order.
**Fix:** Ensure contentTemplates resources `dependsOn` the contentPackages resource.

### "Template variable X is not found"
**Cause:** Referencing a parent-template variable inside a nested `mainTemplate`.
**Fix:** Re-declare the variable in the nested template's `variables` section, or pass it as a parameter.

### "Connect" Button Hangs Indefinitely
The "Starting deployment" notification never completes. Troubleshooting:
1. Test the API manually from your machine (curl/Postman) — confirm credentials work
2. Check if source API blocks Azure/Microsoft IP ranges
3. Check Sentinel health diagnostics for the connector
4. Verify network connectivity from Azure to the source API
5. Test from an Azure VM in the same region

### 429 Rate Limit Errors
**Cause:** Pagination bursts — many pages fetched in rapid succession.
**Mitigations:**
- Maximize page size to reduce total pages
- Increase `retryCount` (max 6)
- Increase `timeoutInSeconds`
- Use `rateLimitConfig` to read rate limit headers
- Stagger `queryWindowInMin` across connectors
- Increase polling interval (trades latency for reliability)

### Data Not Appearing After Connect
- Wait up to 30 minutes — initial ingestion has a delay
- Check DCR health metrics in Azure Monitor
- Verify the custom table exists in the workspace
- Check that `streamName` in dcrConfig matches the DCR's `streamDeclarations`
- Verify `outputStream` in dataFlows matches the table name

### "content template $XxxConnectorDefinition not found"
The Connect button fails with this error when the Sentinel Portal cannot locate the deployed content template. Three distinct root causes:

**Cause 1: ConnectorDefinition contentTemplate has `dependsOn` on Connections contentTemplate**
The ConnectorDefinition contentTemplate (`contentKind: "DataConnector"`) must depend ONLY on contentPackages. If it also depends on the Connections contentTemplate (`contentKind: "ResourcesDataConnector"`), ARM may deploy them in an order the Portal doesn't expect, causing it to fail to locate the definition template.
**Fix:** Remove the Connections contentTemplate from the ConnectorDefinition's `dependsOn` array. Only keep the contentPackages dependency.

**Cause 2: Connections metadata `parentId` points to non-existent resource**
The metadata resource inside the Connections contentTemplate has a `parentId` that must reference an actually-deployed resource. For multi-poller connectors, there is no single poller resource to reference.
**Fix:** For multi-poller connectors, point `parentId` to the `dataConnectorDefinitions` resource (which always exists). For single-poller connectors, point to the `dataConnectors` resource.

**Cause 3: Connections `contentProductId` uses wrong prefix**
The `contentProductId` on the Connections contentTemplate must use the `'rdc'` prefix (for `ResourcesDataConnector`), not `'dc'` (which is for `DataConnector`). Using the wrong prefix causes the Portal to look in the wrong content category.
**Fix:** Change the prefix from `'-','dc','-'` to `'-','rdc','-'` in the `contentProductId` expression.

### "InvalidOutputTable: Table not available for destination"
```
InvalidOutputTable: Table for output stream 'Custom-TableName_CL' is not
available for destination 'clv2ws1'.
```
**Cause:** Custom table resources defined only inside a `contentTemplate.mainTemplate` are NOT created during ARM deployment -- they are stored as a definition for Content Hub but do not actually exist in the workspace. When the Connect button creates the DCR, it references tables that don't yet exist.
**Fix:** Add custom tables as **top-level resources** in the outer ARM template (outside any contentTemplates) so they are actually deployed and exist before the Connect button creates the DCR. Use `"name": "[concat(parameters('workspace'), '/', variables('_logAnalyticsTableId1'))]"` for top-level table names (the workspace prefix is required at the top level, unlike inside nested templates).

This error can also occur when deleting tables and redeploying too quickly -- Azure has soft-delete propagation delays. Wait a few minutes before redeploying after table deletion.

### Table Resources Inside contentTemplate mainTemplate
Table resources (`Microsoft.OperationalInsights/workspaces/tables`) inside `contentTemplate.mainTemplate` have special constraints:

- **Must NOT have `"kind": null`** -- omit the `kind` property entirely. Setting it to `null` causes validation errors.
- **Must NOT have `location`** -- omit the `location` property. The Content Hub scopes table resources to the workspace automatically; including `location` causes conflicts.
- **Must use table-name-only naming** -- use `"name": "MyTable_CL"`, not `"name": "[concat(parameters('workspace'), '/MyTable_CL')]"`. The Portal adds workspace scoping automatically.

### KQL Transform Errors
- Check for blank lines in `transformKql`
- Verify all functions are in the supported list
- Check quote escaping in JSON (`\"` for quotes within KQL)
- Ensure `TimeGenerated` is produced
- Test transform in Log Analytics first

## Health Monitoring

### DCR Health Metrics (Azure Monitor)
| Metric | What It Tells You | Target |
|--------|-------------------|--------|
| Logs Transformation Duration per Min | Transform execution time | Well under 20 seconds |
| Logs Transformation Errors per Min | Transform failures | Zero |
| Logs Rows Received per Min | Data volume flowing | Consistent, non-zero |
| Logs Rows Dropped per Min | Data being discarded | Zero (or expected if filtering) |

### Sentinel Data Connector Health
Navigate to: Sentinel > Configuration > Data connectors > [your connector] > Health
- Shows connection status
- Last data received timestamp
- Error messages

### Enable Diagnostic Logging for DCR
```json
{
    "type": "Microsoft.Insights/diagnosticSettings",
    "properties": {
        "logs": [{ "category": "LogErrors", "enabled": true }],
        "metrics": [{ "category": "AllMetrics", "enabled": true }]
    }
}
```

## Network Requirements

### Scuba Service Tag
The CCF uses Azure IP addresses tagged with the **Scuba** service tag. If your source API requires IP allowlisting:

1. Find current IPs:
```bash
# Use Service Tag Discovery API
az network list-service-tags --location eastus --query "values[?name=='Scuba']"
```

2. Add these IPs to your source API's allowlist

### Testing from Azure
Source APIs may work from your local machine but fail from Azure. Test connectivity from:
- An Azure VM in the same region as your Sentinel workspace
- An Azure Function in the same region
- Using the Azure Cloud Shell

## Content Hub Packaging

See also: `scripts/README.md` for the full packaging scripts guide, and `reference/ccf-packaging-details.md` for CCF-specific packaging rules (folder naming, file suffixes, multi-poller patterns, connector kinds).

### Solution Folder Structure
```
Solutions/
└── MySolution/
    ├── Data/
    │   └── Solution_MySolution.json
    ├── SolutionMetadata.json
    ├── ReleaseNotes.md
    └── Data Connectors/
        └── MySolutionLogs_ccf/
            ├── MySolution_connectorDefinition.json
            ├── MySolution_PollerConfig.json
            ├── MySolution_DCR.json
            └── MySolution_Table.json    (optional — only for custom tables)
```

### Solution Metadata Fields
```json
{
    "Name": "MySolution",
    "Author": "Company - email",
    "Description": "Solution description",
    "Data Connectors": ["Data Connectors/MySolutionLogs_ccf/MySolution_connectorDefinition.json"],
    "BasePath": "C:\\path\\to\\Azure-Sentinel\\Solutions\\MySolution",
    "Version": "3.0.0",
    "Metadata": "SolutionMetadata.json",
    "TemplateSpec": true,
    "Is1PConnector": false
}
```

### Separate-File Format (Used in Solutions/)

Production connectors in the `Solutions/` directory use **separate JSON files** rather than a single ARM template. The packaging tool (`createSolutionV3.ps1`) merges them into the final `mainTemplate.json` for Content Hub deployment.

**Common file layout:**
```
Solutions/
└── MySolution/
    └── Data Connectors/
        └── MySolutionLogs_ccf/
            ├── MySolution_connectorDefinition.json   (UI definition, kind: Customizable)
            ├── MySolution_PollerConfig.json           (one or more RestApiPoller connection configs)
            ├── MySolution_DCR.json                    (Data Collection Rule)
            └── MySolution_Table.json                  (optional — only for custom tables)
```

**Placeholder syntax:**

| Syntax | When It's Resolved | Example |
|--------|-------------------|---------|
| `{{placeholder}}` | At connect-time by the CCF platform | `{{dataCollectionEndpoint}}`, `{{apiKey}}`, `{{location}}` |
| `[[parameters('name')]` | At ARM deployment time (nested template) | `[[concat(parameters('Domain'),'/api/v2/logs')]` |

`{{placeholder}}` values map to UI input fields by `name`. Common platform-provided placeholders:
- `{{dataCollectionEndpoint}}`, `{{dataCollectionRuleImmutableId}}`, `{{dataCollectionEndpointId}}`
- `{{workspaceResourceId}}`, `{{location}}`

**Key differences from single-ARM-template format:**
- No ARM resource wrappers — just the `properties` content
- PollingConfig is a JSON array of connector objects (each with `kind: "RestApiPoller"`)
- DCR is the raw DCR resource (no contentTemplates wrapper)
- The packaging tool adds ARM boilerplate, contentPackages, contentTemplates, dependencies, and metadata

When building a connector from scratch, you can author in either format. The separate-file format is easier to read and edit; the packaging tool handles ARM template generation.

### Packaging Command
```powershell
cd Tools/Create-Azure-Sentinel-Solution/V3
.\createSolutionV3.ps1
# When prompted, provide: <REPO_ROOT>/Solutions/MySolution/Data
```

## Example Connectors on GitHub
All under https://github.com/Azure/Azure-Sentinel/tree/master/Solutions/

**RestApiPoller examples:**
- Ermes Browser Security
- Palo Alto Prisma Cloud CWPP
- Sophos Endpoint Protection
- Workday
- Atlassian Jira
- Okta Single Sign-On

**GCP examples:**
- GCP audit logs
- GCP security command center

Study these for real-world patterns of auth, pagination, DCR, and transforms.

## Source API Preparation Checklist
Before building a connector, document:
- [ ] Authentication mechanism (which CCP auth type maps to it)
- [ ] Rate limits (requests per minute/second, per-key vs per-environment)
- [ ] Rate limit response headers (for `rateLimitConfig`)
- [ ] Pagination model (cursor, offset, link header, cookie)
- [ ] Query time parameter format
- [ ] Server-side filtering capabilities
- [ ] Estimated production log volume
- [ ] Whether Azure IP ranges are blocked
- [ ] Response format (JSON, CSV, XML, compressed)
- [ ] Whether endpoint supports time-range queries (vs streaming/tail)
