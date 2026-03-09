# Solution Packaging with createSolutionV3.ps1

**When to use:** After building the individual connector files (definition, poller config, DCR, table), use this guide to package them into a deployable Sentinel solution.

**See also:**
- `scripts/README.md` — Full script guide: prerequisites, script architecture, data input format
- `reference/ccf-packaging-details.md` — CCF-specific rules: folder naming, file suffixes, multi-poller patterns, connector kinds

---

## Building Block Files

Every CCP connector solution requires 4 building block JSON files:

| File | Purpose | File Suffix |
|------|---------|-------------|
| **ConnectorDefinition** | Connector UI metadata, instructions, connectivity criteria | `_connectorDefinition` |
| **PollerConfig** | RestApiPoller connection rules (request, response, auth, paging) | `_PollerConfig` |
| **DCR** | Data Collection Rule with stream declarations, transforms, dataFlows | `_DCR` |
| **Table** (optional) | Custom table schema (`_CL` suffix) with column definitions | `_Table` |

File naming example: `PaloAltoPrismaCloudCWPP_connectorDefinition.json`, `PaloAltoPrismaCloudCWPP_PollerConfig.json`, etc.

### Key Field Mappings Across Files

These identifiers must match across files — a mismatch causes silent deployment failures:

```
ConnectorDefinition.id
    └─► PollerConfig.connectorDefinitionName    (must match definition id)
        └─► DCR.streamDeclarations.streamName   (must match dcrConfig.streamName in poller)
            └─► Table.schema.name               (must match DCR outputStream target)
```

- **Definition `id`** → referenced by `connectorDefinitionName` in the poller config
- **Stream name** (`Custom-{TableName}_CL`) → appears in DCR `streamDeclarations`, DCR `dataFlows.streams`, and poller `dcrConfig.streamName`
- **Table name** (`{Name}_CL`) → appears in table `schema.name`, DCR `dataFlows.outputStream` (`Custom-{Name}_CL`), and definition `graphQueriesTableName`

### Data Connectors Array Rule

In the solution data file (`Solution_{Name}.json`), the `Data Connectors` array should **only list the definition file path**. The packager auto-discovers the corresponding poller, DCR, and table files by following the cross-file mappings above. Do not add poller, DCR, or table paths to this array.

## Metadata Files

In addition to the 4 building blocks, the solution needs:

| File | Purpose |
|------|---------|
| `Solution_{Name}.json` | Solution manifest — lists all building block files, content types, version |
| `SolutionMetadata.json` | Marketplace metadata — publisher, support info, categories |
| `ReleaseNotes.md` | Version history for the solution |

### Solution Manifest (`Solution_{Name}.json`)

Key fields:
- `Name` — solution display name
- `Version` — semver string (e.g., `"3.0.0"`)
- `Data Connectors` — array of paths to **definition files only** (poller/DCR/table are auto-discovered)
- `Metadata` — path to `SolutionMetadata.json`

See `scripts/README.md` for the complete data input file format reference.

## Folder Structure

```
Solutions/
  {SolutionName}/
    Data/
      Solution_{SolutionName}.json        ← data input file (packager reads this)
    Data Connectors/
      {CompanyProduct}Logs_ccf/           ← CCF naming convention (see ccf-packaging-details.md)
        {Name}_connectorDefinition.json
        {Name}_PollerConfig.json
        {Name}_DCR.json
        {Name}_Table.json                 ← optional (only for custom tables)
    SolutionMetadata.json
    ReleaseNotes.md
    Package/                              ← output directory (generated)
      mainTemplate.json
      createUiDefinition.json
      {SolutionName}_x.x.x.zip
```

## Running createSolutionV3.ps1

The packager script reads the solution manifest and building blocks, then generates the ARM template and UI definition. Run it from within the cloned Azure-Sentinel repo.

### Parameters

```powershell
cd C:\Repos\Azure-Sentinel\Tools\Create-Azure-Sentinel-Solution\V3

# Catalog mode (default) — fetches version from Sentinel catalog API
.\createSolutionV3.ps1 -SolutionDataFolderPath "C:\Repos\Azure-Sentinel\Solutions\{SolutionName}\Data"

# Local mode — reads version from local data file and bumps it
.\createSolutionV3.ps1 `
  -SolutionDataFolderPath "C:\Repos\Azure-Sentinel\Solutions\{SolutionName}\Data" `
  -VersionMode local `
  -VersionBump patch
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `-SolutionDataFolderPath` | *(prompted)* | Absolute path to the solution's `Data/` folder. Must be under a `Solutions/` directory. |
| `-VersionMode` | `catalog` | `catalog` = fetch version from Sentinel catalog API; `local` = read from local data file |
| `-VersionBump` | `patch` | `patch`, `minor`, or `major`. Only used with `-VersionMode local`. |

The path must contain `Solutions` as a path segment and end with `/Data`. The script derives `repositoryBasePath` from this path to locate its dependencies. See `scripts/README.md` for details on path resolution.

### Version Modes

- **Catalog mode** (default): Queries the Sentinel solutions catalog API for the current published version and increments it
- **Local mode**: Reads the `Version` field from `Solution_{Name}.json` and bumps by the specified increment type
- **New solution:** Set `Version` to `"3.0.0"` (minimum for CCF)
- The version flows into `_solutionVersion` in the generated `mainTemplate.json`

### Output

The packager produces files in `Solutions/{SolutionName}/Package/`:

1. **`mainTemplate.json`** — complete ARM template with all 5 resources (contentPackages, contentTemplates x2, dataConnectorDefinitions, metadata), properly escaped bracket expressions, and dependency chains
2. **`createUiDefinition.json`** — Azure Portal deployment UI with parameter inputs mapped to the ARM template parameters
3. **Versioned zip** — `{SolutionName}_{Version}.zip` containing both files, ready for Marketplace or manual deployment

### Post-Packaging Validation

After running the packager:
- Cross-validate that every `outputs` parameter in `createUiDefinition.json` matches a declared `parameters` entry in `mainTemplate.json`
- Verify `_solutionVersion` in the generated template matches the manifest version
- Spot-check bracket escaping: `[[` in nested templates, single `[` at parent level
- Confirm the dependency chain: all resources `dependsOn` the contentPackages resource
