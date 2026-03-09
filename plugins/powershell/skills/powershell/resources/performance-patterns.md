# PowerShell Performance Patterns

Benchmark data sourced from [Microsoft Learn — Script Authoring Performance Considerations](https://learn.microsoft.com/en-us/powershell/scripting/dev-cross-plat/performance/script-authoring-considerations) (Windows 11 / PS 7.3–7.4) unless otherwise noted.

---

## Collection Building: Never `+=` in Loops

Array `+=` creates a new array, copies all elements, then appends — **O(n²)**:

| Items | `+=` | Direct assignment | Difference |
|---|---|---|---|
| 102,400 | 202,000 ms | 11 ms | **18,067×** |

```powershell
# ✅ FASTEST: Capture foreach output directly (CLM-safe, no intermediate variable)
$results = foreach ($item in $inputData) {
    [PSCustomObject]@{
        Name   = $item.Name
        Status = Get-Status -Item $item
    }
}

# ✅ WHEN MUTATION NEEDED: Generic List (FullLanguage only — CLM-unsafe)
$list = [System.Collections.Generic.List[string]]::new()
foreach ($file in Get-ChildItem -Path $path -File) {
    $list.Add($file.FullName)   # List<T>.Add() returns void — no suppression needed
}

# ❌ NEVER: += in loops
$results = @()
foreach ($item in $inputData) {
    $results += $item   # O(n²) — 18,067x slower at 102K items
}
```

---

## String Building: Use `-join`, Never `+=`

String `+=` is **790× slower** than `-join` at 102,400 iterations. Remarkably, `-join` also outperforms `StringBuilder` (86 ms vs 499 ms):

```powershell
# ✅ FASTEST: -join operator
$report = @(foreach ($entry in $logEntries) {
    "$($entry.Timestamp) - $($entry.Message)"
}) -join "`n"

# ✅ ALSO GOOD: pipeline with -join
$csv = $users | ForEach-Object { "$($_.Name),$($_.Email)" } | Out-String

# ❌ NEVER: string += in loops
$report = ''
foreach ($entry in $logEntries) {
    $report += "$($entry.Timestamp) - $($entry.Message)`n"   # 790× slower
}
```

---

## Cross-Collection Correlation: Hashtable Lookups

Nested `Where-Object` for joins is **O(n × m)** — turns seconds into minutes at scale:

```powershell
# ✅ CORRECT: Hashtable lookup — O(n + m)
$accountLookup = @{}
foreach ($account in $accounts) {
    $accountLookup[$account.UPN] = $account
}
foreach ($employee in $employees) {
    $match = $accountLookup[$employee.Email]
    if ($null -ne $match) {
        [PSCustomObject]@{
            Employee  = $employee.Name
            UPN       = $match.UPN
            LastLogon = $match.LastLogon
        }
    }
}

# ❌ AVOID: Nested Where-Object — O(n × m), minutes for 10K × 5K
foreach ($employee in $employees) {
    $match = $accounts | Where-Object { $_.UPN -eq $employee.Email }
}
```

---

## Object Creation

| Operation | Slow | Fast | Speedup |
|---|---|---|---|
| Create PSObject | `New-Object PSObject` | `[PSCustomObject]@{}` | **~7×** |
| Create .NET type | `New-Object StringBuilder` | `[StringBuilder]::new()` | **~5×** |
| Dynamic properties | `Add-Member` per property | `[ordered]` + `[pscustomobject]` cast | **~37×** |
| File exists | `Test-Path` | `[System.IO.File]::Exists()` | ~5× (community benchmark) |

```powershell
# ✅ Fast object creation
$obj = [PSCustomObject]@{ Name = $name; Value = $value }

# ✅ Fast .NET type instantiation (FullLanguage only)
$sb = [System.Text.StringBuilder]::new()

# ✅ Fast dynamic object via [ordered] cast (37× faster than Add-Member loop)
$properties = [ordered]@{}
$properties['Name']  = $name
$properties['Value'] = $value
$obj = [pscustomobject]$properties

# ❌ Slow
$obj = New-Object -TypeName PSObject -Property @{ Name = $name }
$obj | Add-Member -NotePropertyName 'Value' -NotePropertyValue $value
```

---

## Filtering: Filter Left, Filter Early

| Technique | When to Use |
|---|---|
| Provider `-Filter` | File system, AD, registry — server-side, fastest |
| `.Where()` method | In-memory collections — avoids pipeline overhead |
| `Where-Object` | Pipeline streaming from cmdlets |

```powershell
# ✅ Provider-level filter (server-side)
Get-ChildItem -Path $logDir -Filter '*.log' -Recurse
Get-ADUser -Filter { Department -eq 'Finance' -and Enabled -eq $true }

# ✅ .Where() for in-memory collections
$expiredCerts = $allCerts.Where({ $_.NotAfter -lt [datetime]::Now })

# ✅ .Where() with 'First' mode — early exit (stops at first match)
# Microsoft benchmark: 2.6ms vs 633ms on 1M items vs collection comparison operator
$firstExpired = $allCerts.Where({ $_.NotAfter -lt [datetime]::Now }, 'First')

# ❌ Pulls everything into the pipeline first
Get-ChildItem -Path $logDir -Recurse | Where-Object { $_.Extension -eq '.log' }
```

---

## `foreach` Statement vs `ForEach-Object` Cmdlet

The `foreach` **statement** avoids all pipeline overhead. Community benchmarks (powershell.one, 100K iterations):
- Without scriptblock logging: **6.5× faster**
- With scriptblock logging enabled: **167× faster**

```powershell
# ✅ foreach statement — no pipeline, break/continue work normally
foreach ($user in $allUsers) {
    if (-not $user.Enabled) { continue }
    $user.Name
}

# ForEach-Object — required for pipeline streaming; processes one object at a time
# Use when: data comes from a cmdlet and you don't want to load it all into memory first
Get-ChildItem -Path $largePath -Recurse | ForEach-Object {
    $_.FullName
}

# ForEach-Object -Parallel (PS7+) — for I/O-bound work only
# Runspace creation overhead makes it slower than foreach for CPU-bound loops
$results = $urls | ForEach-Object -Parallel {
    Invoke-RestMethod -Uri $_
} -ThrottleLimit 10
```

---

## Output Suppression Performance

At scale (102,400 iterations), `$null =` and `[void]` are within 5% of each other. Only `Out-Null` has meaningful overhead:

| Method | Overhead |
|---|---|
| `$null = expr` | Baseline |
| `[void](expr)` | Equivalent (≤5% difference) |
| `expr > $null` | Equivalent (≤5% difference) |
| `expr \| Out-Null` | **~1.5× slower** in PS7 (much worse in PS5.1) |

```powershell
# ✅ Use either — functionally equivalent, pick for readability
$null = $list.Add($item)
[void]$list.Add($item)

# ❌ Avoid in hot paths
$list.Add($item) | Out-Null
```

---

## Function Call Overhead

Calling a function **inside** a loop is ~6.5× slower than putting the loop **inside** the function (repeated scope creation + parameter binding). Structure hot paths accordingly:

```powershell
# ✅ Loop inside the function — one scope creation
function Process-AllItems {
    [CmdletBinding()]
    param([object[]]$Items)
    foreach ($item in $Items) {
        # process $item
    }
}
Process-AllItems -Items $largeCollection

# ❌ Function inside the loop — scope created 10,000 times
foreach ($item in $largeCollection) {
    Process-SingleItem -Item $item
}
```

---

## Large File Processing

```powershell
# ✅ Fast native approach: switch -File (reads line-by-line, no array allocation)
$errors   = [System.Collections.Generic.List[string]]::new()
$warnings = 0
switch -Regex -File $logPath {
    '^ERROR' { $errors.Add($_) }
    '^WARN'  { $warnings++ }
}

# ✅ Fastest .NET approach for very large files (FullLanguage only)
foreach ($line in [System.IO.File]::ReadLines($logPath)) {
    if ($line.StartsWith('ERROR')) { $errors.Add($line) }
}

# ❌ Slow — loads entire file into memory as string array
$lines = Get-Content -Path $logPath
```

---

## `[datetime]::Now` vs `Get-Date` in Hot Paths

Community benchmarks report `[datetime]::Now` as ~10× faster than `Get-Date` in tight loops. The absolute difference per call is sub-millisecond — only matters in loops with thousands of iterations.

```powershell
# ✅ In tight loops (FullLanguage only)
$timestamp = [datetime]::Now

# Fine everywhere else
$timestamp = Get-Date -Format 'o'
```

---

## Module Manifest: Explicit `FunctionsToExport`

`FunctionsToExport = '*'` forces PowerShell to perform expensive module analysis during command auto-discovery. Microsoft documentation states this can add ~15 seconds on a fresh system.

```powershell
# ✅ Explicit export list in .psd1 — fast discovery
@{
    FunctionsToExport = @('Get-Widget', 'Set-Widget', 'Remove-Widget')
    CmdletsToExport   = @()
    AliasesToExport   = @()
    VariablesToExport = @()
}

# ❌ Wildcard — forces full module analysis
@{
    FunctionsToExport = '*'
}
```
