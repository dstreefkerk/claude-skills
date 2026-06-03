# Common PowerShell Patterns

## Script skeleton

```powershell
#Requires -Version 5.1
#Requires -Modules Az.Accounts

<#
.SYNOPSIS
    One-line summary.
.DESCRIPTION
    Longer description.
.PARAMETER InputPath
    Path to the input file.
.EXAMPLE
    .\Invoke-MyScript.ps1 -InputPath C:\data\input.csv
#>
[CmdletBinding(SupportsShouldProcess)]
param (
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string] $InputPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

#region Functions

function Get-Something {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory)]
        [string] $Name
    )

    # ...
}

#endregion Functions

#region Main

try {
    # main logic
}
catch {
    $err = $_
    throw $err  # re-throw to preserve original error record and halt execution
}
finally {
    # cleanup: close connections, stop transcripts, etc.
}

#endregion Main
```

## Error handling

```powershell
try {
    $result = Get-Item -Path $filePath -ErrorAction Stop
}
catch [System.IO.FileNotFoundException] {
    $err = $_
    Write-Warning "File not found: $($err.Exception.Message)"
}
catch {
    $err = $_
    $PSCmdlet.ThrowTerminatingError($err)  # re-throw for critical failures
}
finally {
    # always runs — close handles, connections, etc.
}
```

## Building collections (not `+=`)

```powershell
# FullLanguage mode: typed generic list (fast, type-safe)
# WARNING: [List[T]]::new() is CLM-unsafe. Use the foreach capture form if CLM is possible.
$results = [System.Collections.Generic.List[PSObject]]::new()

foreach ($item in $items) {
    $results.Add([PSCustomObject]@{
        Name  = $item.Name
        Value = $item.Value
    })
}

# Preferred — capture foreach output directly (works in FullLanguage AND CLM):
$results = foreach ($item in $items) {
    [PSCustomObject]@{
        Name  = $item.Name
        Value = $item.Value
    }
}
```

## Splatting for long parameter lists

```powershell
$invokeParams = @{
    ComputerName  = $ComputerName
    ScriptBlock   = $scriptBlock
    Credential    = $Credential
    ErrorAction   = 'Stop'
}
Invoke-Command @invokeParams
```

## Credentials

```powershell
[Parameter()]
[System.Management.Automation.PSCredential]
[Credential()]
$Credential = [System.Management.Automation.PSCredential]::Empty
```

## `[ordered]` hashtable for JSON with stable property order

```powershell
# Use [ordered] when serialisation order matters (API payloads, config files)
$body = [ordered]@{
    name        = $Name
    displayName = $DisplayName
    enabled     = $true
    properties  = [ordered]@{
        severity = 'High'
        tactics  = @('Persistence', 'Exfiltration')
    }
}
$body | ConvertTo-Json -Depth 10  # Always specify -Depth; default is 2 (silently truncates!)
```

## `$script:` scope for cross-function state

```powershell
# Prefer $script: over $global: for state shared between functions in the same script
$script:RequestCount = 0
$script:FailureCount = 0

function Invoke-ApiCall {
    # ...
    $script:RequestCount++
}
```

## Null coalescing (PS7+ only — not available in PS5.1)

```powershell
# PS7+ only:
$tier     = $control.tier ?? 'Unknown'
$timeout  = $config.TimeoutSeconds ?? 30
$config.Value ??= 'default'  # null-coalescing assignment

# PS5.1-compatible equivalent:
$tier    = if ($null -ne $control.tier) { $control.tier } else { 'Unknown' }
$timeout = if ($null -ne $config.TimeoutSeconds) { $config.TimeoutSeconds } else { 30 }
if ($null -eq $config.Value) { $config.Value = 'default' }
```

## Ternary operator (PS7+ only)

```powershell
# PS7+ only:
$label = $isEnabled ? 'Active' : 'Inactive'

# PS5.1-compatible:
$label = if ($isEnabled) { 'Active' } else { 'Inactive' }
```

## Proper ErrorRecord construction in advanced functions

```powershell
# Use when you need a typed, categorised error — not just throw "message"
# WARNING: [ErrorRecord]::new() is CLM-unsafe. In FullLanguage mode only:
$errorRecord = [System.Management.Automation.ErrorRecord]::new(
    [System.InvalidOperationException]::new("Connection failed: $($err.Exception.Message)"),
    'ConnectionFailed',
    [System.Management.Automation.ErrorCategory]::ConnectionError,
    $TargetObject
)
$PSCmdlet.WriteError($errorRecord)

# CLM-safe alternative — re-throw with context:
Write-Error -Message "Connection failed: $($err.Exception.Message)" -Category ConnectionError -ErrorId 'ConnectionFailed'
```

## HTML encoding when generating HTML output

```powershell
# WARNING: Add-Type is CLM-unsafe. Only use System.Web approach in FullLanguage environments.
Add-Type -AssemblyName System.Web
$safe = [System.Web.HttpUtility]::HtmlEncode($userValue)

# CLM-safe / PS7+ alternative using System.Net.WebUtility (also CLM-unsafe, but whitelisted on some systems):
# The safest universal approach is a manual regex replace for the 5 HTML special chars:
$safe = $userValue -replace '&', '&amp;' -replace '<', '&lt;' -replace '>', '&gt;' `
                   -replace '"', '&quot;' -replace "'", '&#39;'
$html = "<td>$safe</td>"
```

## Native executable exit code check

```powershell
robocopy $source $destination /MIR
if ($LASTEXITCODE -ge 8) {
    throw "robocopy failed with exit code $LASTEXITCODE"
}
```

## Switch parameters

```powershell
# Correct — no default value needed
[switch] $Force

# Wrong — redundant and misleading
[switch] $Force = $false
```

## String interpolation

```powershell
# Correct
"Processing $($item.Name) ($($item.Count) items)"
"Elapsed: {0}ms" -f $stopwatch.ElapsedMilliseconds
"Elapsed: $($stopwatch.ElapsedMilliseconds) ms"  # space before unit avoids parsing ambiguity

# Wrong — string concatenation with +
"Processing " + $item.Name + " (" + $item.Count + " items)"
```

## Here-strings for multi-line content

```powershell
# Double-quoted: supports variable expansion
$body = @"
{
    "name": "$Name",
    "enabled": true
}
"@

# Single-quoted: literal, no expansion
$query = @'
SELECT *
FROM users
WHERE active = 1
'@

# Opening @" must be on same line as @; closing "@ must be at column 0 (no leading spaces)
```

## Path construction (always use `$PSScriptRoot`)

```powershell
# Correct — relative to the script file itself, not the working directory
$configPath = Join-Path -Path $PSScriptRoot -ChildPath 'config.json'
$dataPath   = Join-Path -Path $PSScriptRoot -ChildPath 'data' | Join-Path -ChildPath 'input.csv'

# Wrong — assumes working directory, breaks when called from elsewhere
$configPath = '.\config.json'
```

## Pipeline-accepting function

```powershell
function Invoke-ProcessItem {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory, ValueFromPipeline)]
        [PSObject] $InputObject
    )

    process {
        # process{} runs once per piped object
        [PSCustomObject]@{
            Name   = $InputObject.Name
            Result = 'Processed'
        }
    }
}

# Usage: $items | Invoke-ProcessItem
```

## Parameter validation attributes

```powershell
param (
    [ValidateSet('Read', 'Write', 'ReadWrite', IgnoreCase = $true)]
    [string] $AccessMode = 'Read',

    [ValidateRange(1, 100)]
    [uint32] $MaxRetries = 3,

    [ValidatePattern('^[A-Z]{2,4}-\d+$')]
    [string] $TicketId,

    [ValidateScript({ Test-Path -Path $_ -PathType Leaf })]
    [string] $InputFile
)
```

## Discarding output (performance order: fastest → slowest)

```powershell
[void](Some-Cmdlet)           # Fastest — cast to void, no pipeline
$null = Some-Cmdlet            # Equivalent to [void], clear intent
Some-Cmdlet | Out-Null        # Slowest — creates pipeline, avoid in hot paths
```

## Forcing array output

```powershell
# Single result from a cmdlet is a scalar, not an array — .Count may not exist
$results = Get-SomeThing -Filter $filter

# Force array to guarantee .Count and index access:
$results = @(Get-SomeThing -Filter $filter)
if ($results.Count -eq 0) { return }
```

## Null/empty string check

```powershell
# Correct — handles $null, empty string, and whitespace-only
if ([string]::IsNullOrWhiteSpace($value)) { ... }

# Or for just null/empty (whitespace is OK):
if ([string]::IsNullOrEmpty($value)) { ... }

# Wrong — only catches $null, misses empty string
if ($null -eq $value) { ... }
```

## Safe property accessor (reusable null-safe helper)

When a script reads properties off many objects of unknown or varying shape (API
responses, KQL result rows, pipeline objects), repeating
`if ($obj.PSObject.Properties['X']) { $obj.X }` inline everywhere is noisy and
easy to get wrong. Define one helper and reuse it. Strict-mode-safe by design.

```powershell
function Get-SafeProperty {
    [CmdletBinding()]
    [OutputType([object])]
    param (
        [Parameter(Mandatory)]
        [AllowNull()]
        $InputObject,

        [Parameter(Mandatory)]
        [string] $Name,

        $Default = $null
    )

    if ($null -eq $InputObject) { return $Default }
    if ($InputObject.PSObject.Properties[$Name]) {
        return $InputObject.PSObject.Properties[$Name].Value
    }
    return $Default
}

# Usage — never throws under Set-StrictMode, even if the property is absent:
$status = Get-SafeProperty -InputObject $row -Name 'Status' -Default 'Unknown'
$time   = Get-SafeProperty -InputObject $row -Name 'TimeGenerated'
if ($null -eq $time) { continue }   # column genuinely absent
```

Use this for every field read off external/API/KQL data. Direct access
(`$row.Status`) returns `$null` silently in default PowerShell but throws
`PropertyNotFoundException` under `Set-StrictMode -Version 2+` — and you cannot
control whether a caller has strict mode set in their profile. See
[`traps-and-gotchas.md`](traps-and-gotchas.md) for the inline-guard equivalent.

## Regex patterns

```powershell
# Named capture groups — access via $Matches.<name>
if ($input -match '(?<user>\w+)@(?<domain>[\w.]+)') {
    $user   = $Matches.user
    $domain = $Matches.domain
}

# Escape literal strings for use in regex patterns
$pattern = [regex]::Escape($literalString)
$result  = $input -match $pattern

# Case-sensitive match
if ($input -cmatch '^[A-Z]{3}$') { ... }

# Replace with named backreference
$output = $input -replace '(?<year>\d{4})-(?<month>\d{2})', '${month}/${year}'
```

## Filter at the source, not downstream

```powershell
# GOOD — filter happens server-side or before data enters the pipeline
Get-ChildItem -Path $path -Filter '*.log' -Recurse
Get-ADUser -Filter { Department -eq 'Finance' -and Enabled -eq $true }

# BAD — pulls all objects into pipeline then discards most
Get-ChildItem -Path $path -Recurse | Where-Object { $_.Extension -eq '.log' }
Get-ADUser -Filter * | Where-Object { $_.Department -eq 'Finance' }

# Use Where-Object only when the source cmdlet has no -Filter,
# or for conditions that can't be expressed in the source filter.
```

## Extracting a single property from pipeline objects

```powershell
# GOOD — idiomatic, efficient
$names = Get-Process | Select-Object -ExpandProperty Name

# ACCEPTABLE — works but more verbose
$names = Get-Process | ForEach-Object { $_.Name }

# GOOD — intrinsic method, fastest for in-memory arrays
$names = $processes.ForEach({ $_.Name })   # or: $processes.Name (direct member access)
```

## In-memory collection filtering/transformation

```powershell
# .Where() and .ForEach() are faster than pipeline for in-memory collections (PS4+)
$active = $users.Where({ $_.Enabled -eq $true })
$names  = $users.ForEach({ $_.DisplayName })

# Equivalent pipeline (slower due to overhead, but fine for streaming data from cmdlets)
$active = $users | Where-Object { $_.Enabled -eq $true }
$names  = $users | ForEach-Object { $_.DisplayName }
```

## String building (use `-join`, never `+=`)

```powershell
# ✅ CORRECT: -join operator — 790× faster than += at 102K iterations
$report = @(foreach ($entry in $logEntries) {
    "$($entry.Timestamp) - $($entry.Message)"
}) -join "`n"

# ❌ WRONG: string += in loops — O(n²), 790× slower
$report = ''
foreach ($entry in $logEntries) {
    $report += "$($entry.Timestamp) - $($entry.Message)`n"
}
```

## Cross-collection correlation: hashtable lookups

Nested `Where-Object` for joins is O(n × m) — minutes at scale. Use a hashtable for O(n + m):

```powershell
# ✅ Hashtable lookup — O(n + m)
$accountLookup = @{}
foreach ($account in $accounts) {
    $accountLookup[$account.UPN] = $account
}
foreach ($employee in $employees) {
    $match = $accountLookup[$employee.Email]
    if ($null -ne $match) {
        [PSCustomObject]@{
            Employee = $employee.Name
            Account  = $match.UPN
        }
    }
}

# ❌ Nested Where-Object — O(n × m), minutes for 10K × 5K
foreach ($employee in $employees) {
    $match = $accounts | Where-Object { $_.UPN -eq $employee.Email }
}
```

## `ShouldProcess` + `-Force` pattern

```powershell
function Remove-Widget {
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [switch]$Force
    )

    # Suppress confirmation when -Force is supplied but -Confirm was not explicitly passed
    if ($Force -and -not $PSBoundParameters.ContainsKey('Confirm')) {
        $ConfirmPreference = 'None'   # Scoped to this function only
    }

    if ($PSCmdlet.ShouldProcess($Name, 'Permanently remove widget')) {
        # Destructive operation
    }
}
```

**Note:** `$PSBoundParameters` only contains parameters the caller **explicitly supplied**. Parameters with default values do NOT appear in `$PSBoundParameters` — a common source of incorrect conditional logic.

## Module structure

```
MyModule/
├── MyModule.psd1           # Manifest — explicit FunctionsToExport (never '*')
├── MyModule.psm1           # Root module (dot-sources Public/*.ps1)
├── Public/                 # Exported functions (one per file)
│   ├── Get-Widget.ps1
│   └── Remove-Widget.ps1
└── Private/                # Internal helpers (not exported)
    └── Resolve-WidgetPath.ps1
```

Always list exported functions explicitly in the manifest. `FunctionsToExport = '*'` forces expensive module analysis during command auto-discovery (~15 second penalty on a fresh system):

```powershell
# ✅ In MyModule.psd1
@{
    FunctionsToExport = @('Get-Widget', 'Remove-Widget')
    CmdletsToExport   = @()
    AliasesToExport   = @()
    VariablesToExport = @()
}
```

## `foreach` statement vs `ForEach-Object` cmdlet

```powershell
# foreach STATEMENT:
# - Faster (no pipeline overhead)
# - 'break' and 'continue' work normally
# - 'return' exits the enclosing function/script
foreach ($item in $collection) {
    if ($item.Skip) { continue }   # skip to next
    if ($item.Stop) { break }      # exit loop
    Process-Item -Item $item
}

# ForEach-Object CMDLET:
# - Required for pipeline streaming
# - 'continue' is a syntax error — use 'return' to skip to next item
# - 'return' only exits the current script block iteration, NOT the enclosing script
# - 'break' exits the pipeline entirely (use carefully)
$collection | ForEach-Object {
    if ($_.Skip) { return }     # Skips to next item (NOT an exit — acts like continue)
    Process-Item -Item $_
}
```
