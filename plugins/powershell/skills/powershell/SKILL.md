---
name: powershell
description: Enterprise PowerShell coding standards. Use when writing, reviewing, or generating any PowerShell code, creating PS1 scripts or functions, debugging PowerShell, or asked to help with PowerShell. Enforces best practices for structure, error handling, security, performance, and output patterns.
---

This skill enforces enterprise-grade PowerShell standards when writing, reviewing, or generating any PowerShell code. Apply all rules below automatically — do not wait to be asked.

## Triggers

- "write a PowerShell script"
- "create a function in PowerShell"
- "review this PowerShell"
- "generate a PS1 file"
- "help me with PowerShell code"

---

## Resource Files

Load these when needed for detailed patterns, examples, and gotchas:

| File | When to load |
|---|---|
| [`resources/common-patterns.md`](resources/common-patterns.md) | Need a code pattern (script skeleton, error handling, collections, splatting, regex, pipeline functions, string building, hashtable lookups, module structure, ShouldProcess+Force, etc.) |
| [`resources/compatibility-and-clm.md`](resources/compatibility-and-clm.md) | Need PS5.1 vs PS7+ compatibility details, String.Split() changes, $IsWindows portability, or writing code that may run under AppLocker/WDAC (CLM) |
| [`resources/traps-and-gotchas.md`](resources/traps-and-gotchas.md) | Debugging unexpected behaviour around nulls, booleans, comparison operators, pipeline output pollution, $PSBoundParameters, VerbosePreference in modules, PS class limitations, or defensive null-safe patterns (property access guards, ContainsKey null guards, hashtable key/value guards, null loop entries, Add-Member verification, array double-wrapping) |
| [`resources/get-help-and-get-member.md`](resources/get-help-and-get-member.md) | Using an unfamiliar cmdlet or object — discover parameters, properties, and online docs before writing code |
| [`resources/performance-patterns.md`](resources/performance-patterns.md) | Writing performance-sensitive code — benchmarked patterns for collections, strings, filtering, object creation, hashtable lookups, large file processing, function call overhead |
| [`resources/api-and-web.md`](resources/api-and-web.md) | Calling REST APIs — authentication, pagination, rate limiting/retry, JSON depth, credential management, PSReadLine history protection |
| [`resources/security-hardening.md`](resources/security-hardening.md) | Security controls — CLM enforcement (WDAC vs AppLocker), PowerShell logging (Module/Script Block/Transcription), Protected Event Logging, JEA, code signing, script injection prevention |

---

## Quick Reference

| Area | Rule |
|---|---|
| Structure | `#Requires` → help → `param()` → Functions → Main → Cleanup |
| Strict Mode | `Set-StrictMode -Version Latest` always |
| Indent | 4 spaces, ≤120 chars per line |
| Encoding | UTF-8 without BOM; always specify `-Encoding utf8NoBOM` explicitly |
| Naming | PascalCase functions/params, camelCase locals |
| Functions | Always `[CmdletBinding()]`; Verb-Noun singular nouns |
| State-changing | `SupportsShouldProcess` + `$PSCmdlet.ShouldProcess()` |
| Output | Emit `[PSCustomObject]`; never `Write-Host` for data |
| Errors | `try/catch` with `-ErrorAction Stop`; never empty catch |
| Arrays | Capture `foreach` output directly — never `+=` in loops |
| WMI | `Get-CimInstance` not `Get-WmiObject` |
| Events | `Get-WinEvent` not `Get-EventLog` |
| Secrets | `PSCredential`/`SecureString`/SecretManagement vault — no plaintext |
| Native cmds | Check `$LASTEXITCODE` after native executables; use `try/catch` for cmdlets |
| Aliases | No aliases in scripts — always full cmdlet names |
| Paths | `Join-Path $PSScriptRoot 'file.csv'` — never assume working directory |
| CLM | Check `$ExecutionContext.SessionState.LanguageMode`; avoid `.NET::new()`, `Add-Type` if CLM is possible |

---

## Critical Rules

These are non-negotiable. Apply them to every script and function.

1. **`Set-StrictMode -Version Latest`** at the top of every script (not inside functions).
2. **`[CmdletBinding()]`** on every advanced function, no exceptions.
3. **`-ErrorAction Stop`** on every cmdlet call inside a `try` block, or set `$ErrorActionPreference = 'Stop'` for the scope. Non-terminating errors do NOT trigger `catch` without this.
4. **Never empty `catch` blocks.** Always log at minimum `Write-Warning` or `Write-Error`.
5. **Save `$_` immediately** at the start of a catch block: `$err = $_`
6. **No `+=` in loops.** Capture `foreach` output directly, or use `[System.Collections.Generic.List[PSObject]]::new()` + `.Add()` in FullLanguage mode only.
7. **No `Invoke-Expression`** on untrusted or constructed input — ever.
8. **No plaintext credentials** in code, parameters, or log output.
9. **No aliases** in scripts (`%`, `?`, `gci`, `ft`, etc.).
10. **No `Format-*` mid-pipeline** — emit objects; let the caller format.
11. **`SupportsShouldProcess`** on any function that modifies state (files, registry, AD, etc.).
12. **No `begin/process/end`** at script top level — only inside pipeline-aware functions.
13. **No positional parameters** in scripts — always use named parameters (e.g., `Get-Item -Path $p` not `Get-Item $p`).
14. **Always specify `-Encoding`** on file I/O cmdlets — default encoding differs between PS5.1 and PS7+.

---

## Anti-Patterns

| Anti-Pattern | Replace With |
|---|---|
| `Get-WmiObject` | `Get-CimInstance` |
| `Get-EventLog` | `Get-WinEvent -FilterHashtable @{...}` |
| `$array += $item` in loops | Capture `foreach` output, or `[List[PSObject]]::new()` + `.Add()` |
| `Write-Host` for data output | `Write-Output` / emit objects |
| `Format-Table` mid-pipeline | Emit objects; format at end |
| `Invoke-Expression $cmd` | Parameterised calls / splatting |
| Plaintext password in param | `[PSCredential]` + SecretManagement |
| Empty `catch {}` | Always log or re-throw |
| `$?` after native executables | `$LASTEXITCODE` (for cmdlets use `try/catch`) |
| `ConvertTo-Json` without `-Depth` | Always `ConvertTo-Json -Depth 10` (default 2 silently truncates) |
| `$global:` for cross-function state | `$script:` scope — contained to the script file |
| Building HTML without encoding | Regex replace for 5 HTML special chars (CLM-safe); `HttpUtility` in FullLanguage only |
| `Read-Host` for required input | `[Parameter(Mandatory)]` |
| Aliases (`gci`, `%`, `?`) | Full cmdlet names |
| `begin/process/end` at script top | Only inside pipeline-aware functions |
| Positional parameters (`Get-Item $p`) | Named parameters (`Get-Item -Path $p`) |
| `Out-Null` in hot paths | `[void](...)` or `$null = ...` (no pipeline overhead) |
| `Where-Object` when source has `-Filter` | Use `-Filter` on the source cmdlet |
| `ForEach-Object { $_.Prop }` for single property | `Select-Object -ExpandProperty Prop` |
| `New-Object PSObject -Property @{}` | `[PSCustomObject]@{}` (3x faster, cleaner) |
| `[array]::new()` or `List[T]::new()` in CLM | Capture `foreach` output directly |
| `Add-Type` in potentially CLM environments | Cmdlet-based alternatives |
| `continue` inside `ForEach-Object` | `return` (acts as continue in pipeline context) |
| `if ($array -eq $null)` | `if ($null -eq $array)` (left-side null check) |
| `if ($results)` to test for empty collection | `if ($results.Count -gt 0)` |
| `-Encoding utf8` without knowing PS version | `-Encoding utf8NoBOM` (explicit, portable) |
| `"abc" -contains "ab"` for substring | `"abc".Contains("ab")` or `"abc" -match "ab"` |
| `-like "pattern\d+"` (regex in glob) | `-match "pattern\d+"` for regex patterns |
| `String "False"` as a boolean | Explicit `-eq 'True'` or `-eq $true` comparison |
| `$list.Add($item)` on ArrayList | `[void]$list.Add($item)` — `.Add()` returns the index to the pipeline |
| `New-Item`/`New-Object` output leaked | `$null = New-Item ...` or assign to variable |
| `Write-Output $x` (usually) | Just emit `$x` implicitly; use `Write-Output -NoEnumerate` only for arrays |
| Inconsistent output types per code path | Always emit the same type; use error stream for errors |
| No `[OutputType()]` on functions | Declare `[OutputType([PSCustomObject])]` on functions with defined output |
| `Invoke-RestMethod` without `$ProgressPreference` | Set `$ProgressPreference = 'SilentlyContinue'` at script top for non-interactive use |
| Parameter named `Verbose`, `Debug`, `WhatIf`, etc. | These are reserved by `[CmdletBinding()]` — rename to avoid conflicts |
| Parameter named `Error`, `Input`, `Host`, `Args` | These shadow automatic variables — use distinct names |
| `$string += "text"` in loops | `-join` operator (790× faster at scale) |
| Nested `Where-Object` for cross-collection joins | Hashtable lookup — O(n+m) vs O(n×m) |
| `FunctionsToExport = '*'` in manifest | Explicit function list — avoids ~15s import penalty |
| `"str".Split('ab')` for multi-char splitting | `"str".Split([char[]]'ab')` — portable across PS5.1 and PS7+ |
| `if ($IsWindows)` without edition check | `$PSVersionTable.PSEdition -eq 'Desktop' -or $IsWindows` |
| `Invoke-RestMethod -Authentication` + manual `Authorization` header | Use only one — `-Authentication` silently overrides the header |
| `-FollowRelLink` without `-MaximumFollowRelLink` | Always set `-MaximumFollowRelLink` to prevent infinite loops |
| Class method with implicit output | Class methods discard all output except `return` — assign or return explicitly |
| `Import-Module MyModule; [ClassType]::new()` | `using module MyModule` required for class types |
| `hidden` property assumed private | `hidden` properties ARE serialized by `ConvertTo-Json` |
| `$obj.Prop` on object that may lack `Prop` | `if ($obj.PSObject.Properties['Prop']) { $obj.Prop }` — safe under `Set-StrictMode` and avoids `PropertyNotFoundException` |
| `$hash[$key]` without null-guarding the key | `if ($key) { $hash[$key] }` — null key crashes `Dictionary<TKey,TValue>`; guard first |
| `$hash.ContainsKey($key)` without null guard | `$key -and $hash.ContainsKey($key)` — null argument throws on `Dictionary<>` types |
| Loop body with no null guard on `$item` | `if ($null -eq $item) { continue }` at top — API/pipeline collections can contain null entries |
| Building lookup without guarding key or value | Check `if ($id -and $value)` before `$lookup[$id] = $value` — null keys create silent corrupt entries |
| `$connector | Add-Member ...; $connector._Prop` | Verify with `if ($obj.PSObject.Properties['_Prop'])` — `Add-Member` silently fails on read-only objects |
| `return ,$array` in function + `@(Func)` at call site | Double-wrap bug: `$items = @(Func)` when function returns `,$arr` gives a 1-element wrapper; use direct assignment `$items = Func` |

---

## Review Checklist

Before finalising any generated PowerShell, verify:

- [ ] `Set-StrictMode -Version Latest` present at script top
- [ ] `[CmdletBinding()]` on every advanced function
- [ ] `-ErrorAction Stop` on all cmdlet calls in `try` blocks (or `$ErrorActionPreference = 'Stop'` set)
- [ ] No empty `catch` blocks; `$err = $_` saved at catch start
- [ ] No `+=` inside loops for collection building
- [ ] No aliases used anywhere
- [ ] No `Write-Host` used for data (only acceptable for interactive UI messaging)
- [ ] No `Invoke-Expression` on dynamic/user-supplied input
- [ ] No plaintext secrets in code or output
- [ ] `SupportsShouldProcess` on all state-modifying functions
- [ ] `finally` block for any resource cleanup
- [ ] Output is objects (`[PSCustomObject]`), not pre-formatted strings
- [ ] `Get-CimInstance` used instead of `Get-WmiObject`
- [ ] `$LASTEXITCODE` checked after every native executable call
- [ ] `$PSScriptRoot` used for all paths relative to the script file
- [ ] Parameter variables not mutated; copied to local variables first
- [ ] Lines ≤120 characters; 4-space indentation throughout
- [ ] No positional parameter usage — all parameters named explicitly
- [ ] `-Encoding utf8NoBOM` specified on all file I/O operations
- [ ] `$null` is on the LEFT side of all null comparisons
- [ ] Empty collection checked with `.Count -eq 0`, not bare `if ($collection)`
- [ ] `@($results)` used when `.Count` is needed on cmdlet output
- [ ] `return` (not `continue`) used to skip items in `ForEach-Object`
- [ ] CLM-unsafe patterns (`.NET::new()`, `Add-Type`) avoided if script may run under AppLocker/WDAC
- [ ] PS7-only syntax (`??`, `? :`, `-Parallel`) annotated or avoided if PS5.1 support required
- [ ] `-Filter` used on source cmdlets rather than downstream `Where-Object` where possible
- [ ] `-like` used for glob patterns, `-match` used for regex — not mixed
- [ ] `-contains`/`-in` used for collection membership, not string substring checks
- [ ] `[void]$list.Add(...)` used when calling `ArrayList.Add()` (it returns the index)
- [ ] Intermediate cmdlets (`New-Item`, `New-Object`, etc.) inside functions have their output suppressed or assigned
- [ ] No parameter names clash with common parameters (`Verbose`, `Debug`, `WhatIf`, `Confirm`, `ErrorAction`, etc.)
- [ ] No parameter names shadow automatic variables (`Error`, `Input`, `Host`, `Args`, `This`)
- [ ] `[OutputType()]` declared on functions that emit a defined object type
- [ ] `$ProgressPreference = 'SilentlyContinue'` set in non-interactive scripts that call `Invoke-WebRequest`/`Invoke-RestMethod`
- [ ] `Write-Host` not used for data — only for interactive UI messages
- [ ] String building in loops uses `-join`, not `+=` (790× slower at scale)
- [ ] Cross-collection joins use hashtable lookup, not nested `Where-Object` (O(n+m) vs O(n×m))
- [ ] Module manifest uses explicit `FunctionsToExport` list, not `'*'` (~15s penalty at import)
- [ ] `String.Split()` with multi-char argument uses `[char[]]` cast for portable behaviour
- [ ] `$IsWindows` portability uses `$PSVersionTable.PSEdition -eq 'Desktop' -or $IsWindows`
- [ ] External/API object property access is guarded: `if ($obj.PSObject.Properties['Prop'])` before `$obj.Prop` (strict-mode-safe)
- [ ] Hashtable keys are null-guarded before indexing: `if ($key) { $hash[$key] }` not bare `$hash[$key]`
- [ ] `ContainsKey()` calls are null-guarded: `$key -and $hash.ContainsKey($key)`
- [ ] Loop bodies guard against null items at the top: `if ($null -eq $item) { continue }`
- [ ] Lookup hashtable population guards both key and value before inserting: `if ($id -and $value) { $lookup[$id] = $value }`
- [ ] `Add-Member` note properties are verified before access: `if ($obj.PSObject.Properties['_Name']) { $obj._Name }`
- [ ] Functions using `return ,$array` convention are called with direct assignment (`$x = Func`), NOT `$x = @(Func)` (double-wrap bug)
