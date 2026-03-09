<#
.SYNOPSIS
    Tests get-ccp-details.ps1 against a CCF connector folder to verify
    Definition -> Poller -> DCR -> Table mapping.

.DESCRIPTION
    Auto-discovers JSON files in the given folder, builds the metadata object
    that createSolutionV3.ps1 would normally provide, calls Get-CCP-Dict, and
    prints the mapping results.

.PARAMETER FolderPath
    Path to the CCP connector folder containing ConnectorDefinition, Poller,
    DCR, and Table JSON files.

.EXAMPLE
    pwsh -File test-ccp-mapping.ps1 -FolderPath "C:\repo\Solutions\MyConnector\Data Connectors\MyConnector_ccp"
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$FolderPath
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Source dependencies
. "$scriptDir/common/commonFunctions.ps1"
. "$scriptDir/common/get-ccp-details.ps1"

# Resolve to absolute path
$FolderPath = (Resolve-Path $FolderPath).Path

# Derive the solution structure from the folder path.
# Expected layout: .../<SolutionName>/Data Connectors/<ConnectorFolder>/
# We need baseFolderPath (parent of solution), solutionName, and DCFolderName.

$connectorFolder = Split-Path $FolderPath -Leaf          # e.g. "MyConnector_ccp"
$dcFolderFull = Split-Path $FolderPath -Parent            # e.g. ".../Data Connectors"
$dcFolderName = Split-Path $dcFolderFull -Leaf            # e.g. "Data Connectors"
$solutionFull = Split-Path $dcFolderFull -Parent          # e.g. ".../SolutionName"
$solutionName = Split-Path $solutionFull -Leaf            # e.g. "SolutionName"
$baseFolderPath = (Split-Path $solutionFull -Parent) -replace '\\', '/'
$baseFolderPath = $baseFolderPath.TrimEnd('/') + '/'

# Build file list relative to baseFolderPath/solutionName/
$relativePrefix = "$dcFolderName/$connectorFolder"
$jsonFiles = Get-ChildItem -Path $FolderPath -Filter *.json -File |
    ForEach-Object { "$relativePrefix/$($_.Name)" }

if ($jsonFiles.Count -eq 0) {
    Write-Host "No JSON files found in $FolderPath" -ForegroundColor Red
    exit 1
}

Write-Host "=== Test CCP Mapping ===" -ForegroundColor Cyan
Write-Host "Solution:    $solutionName"
Write-Host "DC Folder:   $dcFolderName"
Write-Host "Connector:   $connectorFolder"
Write-Host "Base Path:   $baseFolderPath"
Write-Host "Files found: $($jsonFiles.Count)"
Write-Host ""

# Build metadata object
$metadata = [PSCustomObject]@{ $dcFolderName = $jsonFiles }

# Run mapping
$result = Get-CCP-Dict `
    -dataFileMetadata $metadata `
    -baseFolderPath $baseFolderPath `
    -solutionName $solutionName `
    -DCFolderName $dcFolderName

Write-Host ""
Write-Host "=== Results ===" -ForegroundColor Cyan

if ($null -eq $result) {
    Write-Host "FAIL: Get-CCP-Dict returned null" -ForegroundColor Red
    exit 1
}

$records = @($result)
Write-Host "Records returned: $($records.Count)"
Write-Host ""

$allPassed = $true
$i = 0
foreach ($r in $records) {
    Write-Host "--- Record $i ---" -ForegroundColor Yellow
    Write-Host "  Title:            $($r.Title)"
    Write-Host "  Definition ID:    $($r.DCDefinitionId)"
    Write-Host "  Poller Name:      $($r.DCPollerName)"
    Write-Host "  Poller Kind:      $($r.PollerKind)"
    Write-Host "  Poller Stream:    $($r.DCPollerStreamName)"
    Write-Host "  DCR Output:       $($r.DCROutputStream)"
    Write-Host "  Table Output:     $($r.TableOutputStream)"

    # Check mappings
    $defOk = $r.DCDefinitionId -ne ''
    $pollerOk = $r.DCPollerFilePath -ne ''
    $dcrOk = $r.DCRFilePath -ne ''
    $tableOk = $r.TableFilePath -ne ''

    $status = if ($defOk) { "OK" } else { "MISSING" }
    Write-Host "  Definition:       $status" -ForegroundColor $(if ($defOk) { "Green" } else { "Red" })

    $status = if ($pollerOk) { "OK" } else { "MISSING" }
    Write-Host "  Poller File:      $status" -ForegroundColor $(if ($pollerOk) { "Green" } else { "Red" })

    $status = if ($dcrOk) { "OK" } else { "MISSING" }
    Write-Host "  DCR File:         $status" -ForegroundColor $(if ($dcrOk) { "Green" } else { "Red" })

    $status = if ($tableOk) { "OK" } else { "MISSING" }
    Write-Host "  Table File:       $status" -ForegroundColor $(if ($tableOk) { "Green" } else { "Red" })

    if (-not ($defOk -and $pollerOk -and $dcrOk -and $tableOk)) {
        $allPassed = $false
    }

    Write-Host ""
    $i++
}

if ($allPassed) {
    Write-Host "ALL MAPPINGS OK" -ForegroundColor Green
    exit 0
} else {
    Write-Host "SOME MAPPINGS MISSING — check output above" -ForegroundColor Red
    exit 1
}
