# Packaging Scripts Reference

> **These are reference copies.** The scripts are tightly coupled to the Azure-Sentinel repo structure and must be run from within that repo. They are included here so Claude Code can read and understand them when helping debug packaging issues.

## Prerequisites

- **PowerShell 7.1+** (cross-platform)
- **Node.js** (for templating JS scripts)
- **powershell-yaml module**: `Install-Module powershell-yaml -Scope CurrentUser`
- **Cloned Azure-Sentinel repo**: `git clone https://github.com/Azure/Azure-Sentinel.git`

## Running the Packager

Navigate to the V3 directory inside the cloned repo:

```powershell
cd C:\Repos\Azure-Sentinel\Tools\Create-Azure-Sentinel-Solution\V3
```

### Catalog Mode (Default)

Fetches the current version from the Sentinel catalog API and increments it:

```powershell
.\createSolutionV3.ps1 -SolutionDataFolderPath "C:\Repos\Azure-Sentinel\Solutions\{SolutionName}\Data"
```

### Local Mode

Reads the version from the local `Solution_{Name}.json` file and bumps it:

```powershell
.\createSolutionV3.ps1 `
  -SolutionDataFolderPath "C:\Repos\Azure-Sentinel\Solutions\{SolutionName}\Data" `
  -VersionMode local `
  -VersionBump patch    # or minor, major
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `-SolutionDataFolderPath` | string | *(prompted)* | Absolute path to the solution's `Data/` folder. Must be under a `Solutions/` directory. |
| `-VersionMode` | string | `catalog` | `catalog` = fetch version from Sentinel catalog API; `local` = read from local data file |
| `-VersionBump` | string | `patch` | Version increment type: `patch`, `minor`, or `major`. Only used with `-VersionMode local`. |

### Interactive Mode

If `-SolutionDataFolderPath` is not provided, the script prompts:
```
Enter solution data folder path:
```

## Path Resolution

The script derives `repositoryBasePath` by finding `Solutions` in the input path:

```
Input:  C:\Repos\Azure-Sentinel\Solutions\MySolution\Data
                 ↑ repositoryBasePath ends here
Result: C:\Repos\Azure-Sentinel\
```

It then dot-sources dependencies via `$repositoryBasePath + "Tools/Create-Azure-Sentinel-Solution/common/..."`. This is why the scripts **must be run from within the Azure-Sentinel repo** — they resolve relative paths from the `Solutions` directory.

The path must:
- Contain `Solutions` as a path segment
- End with `/Data` or `/data` (case-insensitive)

## Output

Generated files go to `Solutions/{SolutionName}/Package/`:

| File | Description |
|------|-------------|
| `mainTemplate.json` | Complete ARM template with all resources, escaping, and dependencies |
| `createUiDefinition.json` | Azure Portal deployment UI definition |
| `{SolutionName}_{Version}.zip` | Versioned zip of both files, ready for Marketplace or manual deployment |

## Script Architecture

### Dependency Chain

```
createSolutionV3.ps1           (entry point — parameter parsing, path resolution)
  └─► commonFunctions.ps1      (core engine — reads data file, orchestrates content types)
        ├─► createCCPConnector.ps1        (CCF-specific processing — building blocks → ARM resources)
        │     └─► get-ccp-details.ps1     (CCP metadata extraction — connector kind detection, field mapping)
        ├─► standardLogStreams.ps1         (stream→table mappings for standard Log Analytics tables)
        ├─► storageAccountDeploymentTemplate.ps1  (StorageAccountBlobContainer ARM resources)
        └─► summaryRules.ps1              (summary rule processing)
```

### What Each Script Does

| Script | Purpose |
|--------|---------|
| `V3/createSolutionV3.ps1` | Entry point. Parses parameters, resolves paths, loads the data file, calls `commonFunctions.ps1`. |
| `common/commonFunctions.ps1` | Core orchestrator. Reads the solution data file, iterates content types (connectors, workbooks, analytics, parsers, etc.), generates `mainTemplate.json` and `createUiDefinition.json`. |
| `common/createCCPConnector.ps1` | CCF connector processor. Reads the 4 building block files, validates cross-file mappings (definition→poller→DCR→table), generates ARM resources with correct escaping and dependencies. |
| `common/get-ccp-details.ps1` | CCP metadata extractor. Detects connector kind (RestApiPoller, StorageAccountBlobContainer, etc.), extracts UI parameters, maps textbox/dropdown inputs to ARM parameters. |
| `common/standardLogStreams.ps1` | Hashtable mapping standard stream names to Log Analytics table names. Used to validate DCR stream references against known standard tables. |
| `common/storageAccountDeploymentTemplate.ps1` | Generates ARM template resources for StorageAccountBlobContainer connectors (storage queues, Event Grid topics, role assignments). |
| `common/summaryRules.ps1` | Processes summary rule content type for solutions that include summary rules. |

### Templating Files

| File | Purpose |
|------|---------|
| `common/templating/baseMainTemplate.json` | Skeleton ARM template — the packager populates this with resources |
| `common/templating/baseCreateUiDefinition.json` | Skeleton portal UI definition — the packager adds steps and parameters |
| `common/templating/replaceLocationValue.js` | Node.js script that replaces `{{location}}` placeholders with ARM parameter references |
| `common/templating/replacePlaybookParamNames.js` | Renames playbook parameters to avoid conflicts in combined templates |
| `common/templating/replacePlaybookVarNames.js` | Renames playbook variables to avoid conflicts in combined templates |

### ARM Template Test Toolkit

| File | Purpose |
|------|---------|
| `arm-ttk/download-arm-ttk.ps1` | Downloads the ARM template test toolkit from GitHub |
| `arm-ttk/run-arm-ttk-in-automation.ps1` | Runs ARM TTK validation in CI/CD pipelines |

## Data Input File Format

The `Solution_{Name}.json` file in the `Data/` folder drives the entire packaging process.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `Name` | string | Solution display name (must match solution folder name) |
| `Author` | string | Author name and email (e.g., `"Company - email@example.com"`) |
| `Description` | string | Solution description (supports markdown) |
| `Version` | string | Semver version string (minimum `"3.0.0"` for CCF) |
| `BasePath` | string | Base path for resolving relative file references |
| `Metadata` | string | Path to `SolutionMetadata.json` |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `Logo` | string | HTML img tag for solution icon |
| `Data Connectors` | string[] | Paths to connector definition files (for CCF: **only the definition file** — poller, DCR, table are auto-discovered) |
| `Workbooks` | string[] | Paths to workbook JSON files |
| `WorkbookDescription` | string | Description for workbooks |
| `Analytic Rules` | string[] | Paths to analytics rule YAML files |
| `Hunting Queries` | string[] | Paths to hunting query YAML files |
| `Parsers` | string[] | Paths to parser files |
| `Playbooks` | string[] | Paths to playbook ARM templates |
| `TemplateSpec` | bool | Whether to generate as template spec |
| `Is1PConnector` | bool | Whether this is a first-party Microsoft connector |

### Example

See `examples/Solution_ExampleInput.json` for a PingFederate-based example showing the core field structure. Note: this older example predates the `Metadata` and `TemplateSpec` fields — CCF solutions should include both.

## SolutionMetadata.json Format

```json
{
  "publisherId": "azuresentinel",
  "offerId": "azure-sentinel-solution-{name}",
  "firstPublishDate": "2024-01-15",
  "providers": ["CompanyName"],
  "categories": {
    "domains": ["Security - Network"],
    "verticals": []
  },
  "support": {
    "name": "Company Name",
    "email": "support@company.com",
    "tier": "Partner",
    "link": "https://support.company.com"
  }
}
```

| Field | Description |
|-------|-------------|
| `publisherId` | Marketplace publisher ID (`"azuresentinel"` for Microsoft-published) |
| `offerId` | Marketplace offer ID (usually `"azure-sentinel-solution-{name}"`) |
| `firstPublishDate` | ISO date of first publication |
| `providers` | Array of provider/vendor names |
| `categories.domains` | Security domain categories |
| `categories.verticals` | Industry verticals (often empty) |
| `support.tier` | `"Microsoft"`, `"Partner"`, or `"Community"` |

See `examples/SolutionMetadata_ExampleTemplate.json` for a complete example.
