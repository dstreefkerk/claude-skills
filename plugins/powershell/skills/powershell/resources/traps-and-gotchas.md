# PowerShell Traps, Gotchas, and Pipeline Antipatterns

## Boolean and Null Traps

These are among the most common sources of silent bugs in PowerShell.

### `$null` must go on the LEFT side of comparisons

```powershell
# WRONG — when $value is an array, PowerShell filters array elements instead of returning bool
if ($value -eq $null) { }    # If $value is @($null, 1, 2), this returns $null (the element), not $true

# CORRECT — $null on the left, always returns bool
if ($null -eq $value) { }
```

### Empty array is TRUTHY — use `.Count`

```powershell
$results = @()

if ($results) {
    # THIS EXECUTES — empty array is truthy in PowerShell!
}

# CORRECT check:
if ($results.Count -eq 0) { ... }      # Empty
if ($results.Count -gt 0) { ... }      # Non-empty
```

### Single result from a cmdlet may not have `.Count`

```powershell
$result = Get-ADUser -Filter { Name -eq 'Bob' }
# If exactly one result: $result is a single ADUser object, not an array — $result.Count may be $null

# Always force to array when .Count will be used:
$results = @(Get-ADUser -Filter { Department -eq 'IT' })
if ($results.Count -eq 0) { Write-Warning 'No users found'; return }
```

### String `"False"` and other non-empty strings are TRUTHY

```powershell
$value = "False"
if ($value) { "This executes — non-empty string is truthy" }

# Environment variables are strings — "False" is truthy
$env:MY_FLAG = "False"
if ($env:MY_FLAG) { "This executes!" }

# CORRECT: compare the string value explicitly
if ($env:MY_FLAG -eq 'True') { ... }
if ($env:MY_FLAG -ne 'False') { ... }
```

### `return` in `ForEach-Object` skips to next item — it does NOT exit the script

```powershell
# In ForEach-Object, 'return' means "skip to next pipeline item" (like continue)
1..5 | ForEach-Object {
    if ($_ -eq 3) { return }   # Skips 3, does NOT exit the script
    Write-Output $_
}
# Output: 1 2 4 5

# 'continue' is a SYNTAX ERROR inside ForEach-Object — use 'return' instead
1..5 | ForEach-Object {
    if ($_ -eq 3) { continue }  # ERROR: The 'continue' statement is not valid
}

# If you need break/continue semantics, use the foreach statement instead:
foreach ($i in 1..5) {
    if ($i -eq 3) { continue }  # Works correctly
}
```

### `[bool]` vs string coercion

```powershell
# [bool] coercion of strings follows PowerShell rules, not .NET rules
[bool]"False"   # Returns $true — non-empty string
[bool]"0"       # Returns $true — non-empty string
[bool]""        # Returns $false — empty string
[bool]$null     # Returns $false

# Only these values are falsy: $false, $null, 0, 0.0, "" (empty string), @() (empty array — actually truthy, see above!)
```

---

## Comparison Operator Gotchas

### All operators are case-insensitive by default

```powershell
"ABC" -eq "abc"      # $true — insensitive
"ABC" -match "abc"   # $true — insensitive regex
"ABC" -like "abc*"   # $false — no trailing match

# Use 'c' prefix for case-sensitive:
"ABC" -ceq "abc"     # $false
"ABC" -cmatch "abc"  # $false
"ABC" -creplace 'A', 'x'  # 'xBC'

# Use 'i' prefix to be explicit about insensitivity (redundant but self-documenting):
"ABC" -ieq "abc"     # $true
```

### `-contains` is array membership — NOT substring search

```powershell
# -contains: tests if a COLLECTION contains a VALUE (left side must be collection)
$colours = 'red', 'green', 'blue'
$colours -contains 'red'        # $true
$colours -contains 'purple'     # $false

"apple pie" -contains "apple"   # $false — string is not a collection of strings!

# -in: reverse of -contains, cleaner syntax (PS3+)
'red' -in $colours              # $true
'red' -in @('red', 'blue')      # $true

# For substring search, use .Contains() or -match:
"apple pie".Contains("apple")   # $true — .NET method
"apple pie" -match "apple"      # $true — regex match
"apple pie" -like "*apple*"     # $true — wildcard
```

### `-like` uses globs, `-match` uses regex — don't mix them up

```powershell
# -like: glob wildcards only (* = any chars, ? = one char)
"test123" -like "test*"         # $true
"test123" -like "test?"         # $false (? = exactly one char)
"test123" -like "test\d+"       # $false (\d+ is regex, not a glob)

# -match: full regular expressions
"test123" -match "test\d+"      # $true
"test123" -match "test.*"       # $true
"test123" -match "test*"        # $true (but * means "zero or more 't'" in regex — surprising!)

# Rule: use -like for simple wildcard patterns, -match for regex
Get-ChildItem | Where-Object { $_.Name -like "*.log" }  # glob
if ($email -match '^\w+@[\w.]+\.\w+$') { ... }          # regex
```

### `-replace` is case-insensitive regex by default

```powershell
"Hello World" -replace "hello", "Hi"    # "Hi World" — case-insensitive
"Hello World" -creplace "hello", "Hi"   # "Hello World" — case-sensitive (no match)

# Escape literal strings before using as regex patterns:
$literal = "C:\Users\bob"
$escaped = [regex]::Escape($literal)    # Escapes backslashes, etc.
$result  = $input -replace $escaped, $replacement
```

---

## Pipeline Output Antipatterns

PowerShell's object pipeline is its defining feature. These are the most common ways scripts accidentally corrupt, pollute, or misuse it.

### `ArrayList.Add()` silently returns the index to the pipeline

```powershell
# WRONG — .Add() returns the int index (0, 1, 2 ...) which goes straight into the pipeline
$list = [System.Collections.ArrayList]::new()
$list.Add($item)     # Outputs: 0 (then 1, 2 ...) to the caller — silent data corruption

# CORRECT — suppress the return value
[void]$list.Add($item)
$null = $list.Add($item)  # Equivalent alternative

# Note: [System.Collections.Generic.List[T]].Add() returns void — no suppression needed.
# That's one reason to prefer List[T] over ArrayList in FullLanguage mode.
```

### Cmdlets that create/modify items output objects by default

```powershell
# These all write the created/modified item to the pipeline unless suppressed:
New-Item -Path $path -ItemType File           # Outputs FileInfo
Move-Item -Path $src -Destination $dst        # Outputs nothing by default in PS5.1; may vary
Copy-Item -Path $src -Destination $dst        # Outputs nothing by default; use -PassThru to opt-in
Rename-Item -Path $path -NewName $newName     # Outputs nothing by default; use -PassThru to opt-in
New-Object -TypeName SomeType                 # Always outputs the object

# Suppress when you don't want the output:
$null = New-Item -Path $path -ItemType File
[void](New-PSDrive -Name $driveName -PSProvider FileSystem -Root $root)

# Use -PassThru explicitly when you DO want output — makes intent clear:
$newFile = New-Item -Path $path -ItemType File -PassThru
```

### `Write-Output` is redundant in most cases — just emit implicitly

```powershell
# These are functionally identical for pipeline output:
function Get-Value {
    Write-Output 42     # Redundant
}

function Get-Value {
    42                  # Implicit emit — idiomatic PowerShell
}

# The only case where Write-Output adds value: -NoEnumerate
# Without it, emitting an array unrolls it into individual elements:
function Get-Items {
    $arr = @(1, 2, 3)
    Write-Output $arr                        # Emits 3 separate ints
    Write-Output -NoEnumerate $arr           # Emits the array as a single object
}
```

### Every expression in a function body that produces output goes to the pipeline

```powershell
# WRONG — calls to cmdlets/methods inside a function leak output if not suppressed
function Invoke-Setup {
    New-Item -Path $logDir -ItemType Directory    # Leaks FileInfo to pipeline!
    Add-Content -Path $logFile -Value 'Started'  # Outputs nothing (fine)
    [System.Collections.ArrayList]::new()         # LEAKS the ArrayList object!

    # ... real work ...
    [PSCustomObject]@{ Status = 'OK' }           # Intended output
}

# CORRECT — suppress intermediate output explicitly
function Invoke-Setup {
    $null = New-Item -Path $logDir -ItemType Directory
    Add-Content -Path $logFile -Value 'Started'
    $list = [System.Collections.ArrayList]::new()  # Assign, not emit

    [PSCustomObject]@{ Status = 'OK' }
}
```

### Output type should be consistent — never mix types from a single function

```powershell
# WRONG — caller cannot reliably use the output
function Get-Result {
    if ($error) {
        "Something went wrong"   # String
    } else {
        [PSCustomObject]@{ Name = $name; Value = $value }  # Object
    }
}

# CORRECT — always emit the same type; use error stream for errors
function Get-Result {
    [OutputType([PSCustomObject])]
    [CmdletBinding()]
    param()

    if ($badCondition) {
        Write-Error "Something went wrong" -ErrorAction Stop
        return
    }
    [PSCustomObject]@{ Name = $name; Value = $value }
}
```

### Declare `[OutputType()]` on functions with consistent output

```powershell
function Get-ServerInfo {
    [CmdletBinding()]
    [OutputType([PSCustomObject])]    # Documents expected output type for callers and IDEs
    param (
        [Parameter(Mandatory)]
        [string] $ComputerName
    )

    [PSCustomObject]@{
        Name   = $ComputerName
        Uptime = (Get-Date) - (gcim Win32_OperatingSystem).LastBootUpTime
    }
}
```

### Suppress progress output in non-interactive scripts

```powershell
# Invoke-WebRequest, Invoke-RestMethod, Write-Progress all write to the progress stream
# In PS5.1 this renders a progress bar that slows output and clutters logs

# At the top of non-interactive scripts:
$ProgressPreference = 'SilentlyContinue'

# Or per-call:
Invoke-RestMethod -Uri $uri -Headers $headers | Out-Null   # Still shows progress!

# Must suppress the preference, not just Out-Null the result:
$ProgressPreference = 'SilentlyContinue'
$response = Invoke-RestMethod -Uri $uri -Headers $headers
```

### `Write-Host` bypasses the pipeline entirely

```powershell
# Write-Host goes directly to the console — it cannot be captured, redirected, or piped
$output = Write-Host "hello"   # $output is $null — the text went to the screen only
Write-Host "data" | Out-File output.txt   # output.txt is empty!

# In PS5+, Write-Host writes to the Information stream (stream 6), which CAN be redirected:
Write-Host "hello" 6>&1 | Out-File output.txt   # Works — but this is still not the intent

# Rule: Write-Host is only for interactive UI messages (progress indicators, prompts)
#       Never use it for data, status, or anything a caller might want to capture.
# Use instead:
Write-Verbose "Processing $name"   # Captured with -Verbose or $VerbosePreference
Write-Information "Status: OK"     # Stream 6; caller can redirect with 6>&1
Write-Output $obj                  # Or just: $obj
```

---

## `$PSBoundParameters` Does Not Include Default Values

`$PSBoundParameters` only contains parameters the caller **explicitly supplied**. Parameters that use their default values are absent — a common source of bugs in conditional logic:

```powershell
function Set-Config {
    [CmdletBinding()]
    param(
        [string]$Mode = 'Read',
        [switch]$Force
    )

    # WRONG — $Mode is absent from $PSBoundParameters if caller didn't supply it
    if ($PSBoundParameters.ContainsKey('Mode')) {
        "Mode was explicitly set"   # Never runs when default is used
    }

    # CORRECT use of $PSBoundParameters — checking if caller explicitly passed -Confirm
    if ($Force -and -not $PSBoundParameters.ContainsKey('Confirm')) {
        $ConfirmPreference = 'None'
    }
}
```

---

## `$VerbosePreference` Does Not Propagate into Module Functions

Module functions do **not** inherit `$VerbosePreference` from the caller. Calling a module function with `-Verbose` will not produce verbose output from inside the module unless you explicitly capture and forward the preference:

```powershell
function Invoke-ModuleWork {
    [CmdletBinding()]
    param(
        [string]$Task,

        # Capture caller's preference as a default parameter value
        [System.Management.Automation.ActionPreference]$VerbosePreference =
            $PSCmdlet.GetVariableValue('VerbosePreference')
    )

    Write-Verbose "Performing task: $Task"   # Now respects caller's -Verbose
}
```

This pattern is also required for `$DebugPreference` and `$WarningPreference` in module-scoped functions.

---

## PowerShell Classes: Critical Gotchas

Classes (PS 5.0+) have significant limitations that make them unsuitable as a general-purpose replacement for functions and `[PSCustomObject]`.

### Method output is silently discarded

Unlike functions, where every uncaptured expression goes to the pipeline, class method output is **silently dropped** except for explicit `return` values:

```powershell
class FileProcessor {
    [string] GetStatus() {
        "Processing started"   # SILENTLY DISCARDED — not returned!
        return "Complete"      # Only this is returned
    }
}
```

This is the inverse of the pipeline output contamination problem — equally surprising.

### Classes cannot be reloaded

`Import-Module -Force` does **not** reload class definitions. You must restart the entire PowerShell session to pick up class changes.

### `Import-Module` does not export class types

Consumers must use `using module`, not `Import-Module`:

```powershell
# ❌ WRONG — class type not available
Import-Module MyModule
$obj = [ServerInfo]::new()   # ERROR: Unable to find type [ServerInfo]

# ✅ CORRECT
using module MyModule
$obj = [ServerInfo]::new()
```

`using module` requires a literal path or module name — it cannot use variables or expressions, and must appear at the very top of the script file.

### `hidden` does not provide true privacy

Hidden properties are accessible via direct reference and — critically — are **serialized by `ConvertTo-Json`**:

```powershell
class UserProfile {
    [string]$DisplayName
    hidden [string]$InternalId = [guid]::NewGuid().ToString()
}
$user = [UserProfile]@{ DisplayName = 'John' }
$user | ConvertTo-Json   # InternalId IS included in the JSON output
```

### When to use classes vs `[PSCustomObject]`

**Use classes for:**
- State machines with complex internal state
- Implementing .NET interfaces (`IComparable`, `IEquatable`)
- DSC resources
- Argument completers/transformers

**Use `[PSCustomObject]` for everything else** — pipeline-oriented data, simple DTOs, scenarios requiring reloading during development, maximum compatibility.

---

## Reserved and Shadowed Parameter Names

`[CmdletBinding()]` automatically adds **common parameters** to every advanced function. Defining your own parameters with these names will cause a compile error or unexpected behaviour.

### Common parameters added by `[CmdletBinding()]`

Never use these as parameter names:

```
Verbose, Debug, ErrorAction, WarningAction, InformationAction,
ErrorVariable, WarningVariable, InformationVariable,
OutVariable, OutBuffer, PipelineVariable
```

### Additional parameters added by `SupportsShouldProcess`

```
WhatIf, Confirm
```

### Automatic variable names to avoid as parameters

These shadow PowerShell automatic variables and cause confusing bugs:

```powershell
# Don't shadow these in param() blocks:
# $Error         → use $Errors, $ErrorList, $FailedItems
# $Input         → use $InputData, $InputObject (ValueFromPipeline)
# $Args          → use explicit typed parameters
# $Host          → use $HostName, $ComputerName
# $Home          → use $HomePath
# $This          → use $Instance, $Self
# $PSItem        → use $InputObject (the conventional name for pipeline input)

# Example: this shadows $Error automatic variable — all caught errors disappear!
param (
    [string[]] $Error    # BAD — $Error is a reserved automatic variable
)

# CORRECT:
param (
    [string[]] $ErrorMessages
)
```

### Quick check — test for reserved name conflicts

```powershell
# If you get this error, a parameter name clashes with a common/reserved parameter:
# "A parameter with the name 'X' already exists in the parameter set '__AllParameterSets'."
```

---

## Defensive Coding: Null-Safe Object and Collection Patterns

These patterns are critical when working with API responses, KQL results, pipeline output, or any data where schema, shape, or presence cannot be guaranteed. Code defensively as if `Set-StrictMode -Version Latest` is always active — because you cannot control whether callers have it set in their profile.

### Property access on objects with unknown shape

`$obj.SomeProperty` returns `$null` silently in default PowerShell, but throws `PropertyNotFoundException` under `Set-StrictMode -Version 2+`.

```powershell
# WRONG — fails under strict mode if Status property doesn't exist
$healthStatus = if ($health) { $health.Status } else { 'Unknown' }

# CORRECT — check property existence first
$healthStatus = if ($health -and $health.PSObject.Properties['Status']) {
    $health.Status
} else {
    'Unknown'
}
```

This is especially important for:
- KQL/API results where columns/properties vary by customer or schema version
- Objects from `Add-Member` that may have silently failed (see below)
- Pipeline objects that may have a different shape than expected

### Hashtable indexing with potentially null keys

`System.Collections.Hashtable` tolerates null keys; `Dictionary<TKey,TValue>` throws `ArgumentNullException` on null keys.

```powershell
# WRONG — $connectorIdentifier could be $null
$health = $connectorHealthLookup[$connectorIdentifier]

# CORRECT — guard the key
$health = if ($connectorIdentifier) { $connectorHealthLookup[$connectorIdentifier] } else { $null }

# CORRECT — chained fallback pattern
$health = if ($key1) { $lookup[$key1] } else { $null }
if (-not $health -and $key2) { $health = $lookup[$key2] }
if (-not $health -and $key3) { $health = $lookup[$key3] }
```

### `ContainsKey` with null arguments

```powershell
# WRONG — $_.name could be $null; .ContainsKey($null) throws on Dictionary<> types
$withHealth = $group.Group | Where-Object {
    $ConnectorHealthLookup.ContainsKey($_.name) -or
    $ConnectorHealthLookup.ContainsKey($_.kind)
}

# CORRECT — short-circuit with truthiness check first
$withHealth = @($group.Group | Where-Object {
    ($_.name -and $ConnectorHealthLookup.ContainsKey($_.name)) -or
    ($_.kind -and $ConnectorHealthLookup.ContainsKey($_.kind))
})
```

### Null entries in loop bodies

Collections from API pagination, `Group-Object`, or pipeline operations can contain `$null` entries.

```powershell
# WRONG — $item could be $null
foreach ($item in $collection) {
    $name = $item.name
}

# CORRECT — guard at the top of the loop
foreach ($item in $collection) {
    if ($null -eq $item) { continue }
    $name = $item.name
}
```

### Building lookup hashtables defensively

```powershell
# WRONG — silently creates a null-keyed entry; consumers get $null without knowing why
$lookup = @{}
foreach ($item in $items) {
    $lookup[$item.Id] = $item.DisplayName
}

# CORRECT — guard both key and value
$lookup = @{}
foreach ($item in $items) {
    if ($null -eq $item) { continue }
    $id   = $item.Id
    $name = $item.DisplayName
    if ($id -and $name) {
        $lookup[$id] = $name
    }
}
```

### `Add-Member` note properties: verify before reading

`Add-Member` can silently fail on read-only or frozen objects. If it does, the property doesn't exist and access fails under strict mode.

```powershell
# WRONG — assumes Add-Member succeeded
$connector | Add-Member -NotePropertyName '_DisplayName' -NotePropertyValue $name -Force
$label = $connector._DisplayName   # Throws under strict mode if Add-Member failed

# CORRECT — verify the property exists before reading
$label = if ($connector.PSObject.Properties['_DisplayName']) {
    $connector._DisplayName
} else {
    $fallbackValue
}
```

### Functions that return collections — never return `$null` when empty

```powershell
# WRONG — if $collection is empty, $results is $null; ,$null wraps as @($null)
$results = foreach ($item in $collection) { $item }
return ,$results

# CORRECT — guard empty input; wrap foreach in @() to guarantee an array
if (-not $collection -or $collection.Count -eq 0) { return ,@() }

$results = @(foreach ($item in $collection) {
    if ($null -eq $item) { continue }
    $item
})

return ,$results
```

---

## Array Double-Wrapping: `return ,$array` vs `@()` at the Call Site

This is among the most subtle and painful bugs in PowerShell. **Pick one idiom and never mix them.**

### How it happens

Functions use `return ,$results` (the comma operator) to prevent pipeline enumeration — the caller receives the whole array as **one pipeline object**. If the call site then wraps that in `@()`, it produces a one-element array whose only element is the entire inner array.

```
Function pipeline:  ,$results     →  emits one object (the array itself)
@() at call site:   @(one-object) →  @( $results )   ← one-element wrapper
$items.Count = 1
$items[0] = the entire inner array
```

**Symptom:** A table renders one row. The Name column shows `System.Object[]`. Other columns show every value from the collection concatenated.

### The bug in code

```powershell
# Inside the function
return ,$results

# Call site — WRONG: double-wraps the array
$items = @(Get-MyResults -Data $inputData)

foreach ($item in $items) {
    $name = $item.name   # ← "System.Object[]" — you're seeing all names at once
    $kind = $item.kind   # ← all kinds concatenated
}
```

### Correct patterns — pick ONE and apply consistently

**Option A — comma-return + direct assignment (recommended if the codebase already uses this)**

```powershell
# Function
return ,$results

# Call site — direct assignment, NO @()
$items = Get-MyResults -Data $inputData
```

**Option B — no comma-return + `@()` at call site**

```powershell
# Function
return $results   # Pipeline enumerates elements individually

# Call site — collect into array
$items = @(Get-MyResults -Data $inputData)
```

### Quick reference

| Function return   | Call site         | Result                                                     |
|-------------------|-------------------|------------------------------------------------------------|
| `return ,$array`  | `$x = Func`       | `$x` is the array — correct                               |
| `return ,$array`  | `$x = @(Func)`    | **BUG** — `$x` is `@($array)`, a one-element wrapper      |
| `return $array`   | `$x = @(Func)`    | `$x` is the array (elements enumerated then re-collected) |
| `return $array`   | `$x = Func`       | `$x` is scalar if 1 element; `$null` if 0 — use with care |

The comma operator exists precisely to prevent the last row's single-element unwrapping. But then `@()` at the call site must not be used, or the prevention becomes double-wrapping.
