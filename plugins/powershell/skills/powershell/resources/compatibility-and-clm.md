# PS5.1 vs PS7+ Compatibility and Constrained Language Mode

## PS5.1 vs PS7+ Compatibility

When targeting both editions, **use the PS5.1-compatible form** and annotate PS7-only features.

| Feature | PS5.1 | PS7+ | Portable Alternative |
|---|---|---|---|
| `??` null coalescing | ✗ | ✓ | `if ($null -ne $x) { $x } else { $d }` |
| `??=` null assignment | ✗ | ✓ | `if ($null -eq $x) { $x = $d }` |
| `? :` ternary | ✗ | ✓ | `if (...) { x } else { y }` |
| `&&` / `\|\|` pipeline chains | ✗ | ✓ | Separate if statements |
| `ForEach-Object -Parallel` | ✗ | ✓ | Sequential `foreach` |
| `$IsWindows` / `$IsLinux` | ✗ | ✓ (PS6+) | `$Env:OS -eq 'Windows_NT'` |
| `Split-Path -LeafBase` | ✗ | ✓ | `[IO.Path]::GetFileNameWithoutExtension($p)` |
| `-AsHashtable` (ConvertFrom-Json) | ✗ | ✓ (PS6+) | `.PSObject.Properties` iteration |
| `Get-Error` | ✗ | ✓ | `$Error[0] \| Select-Object *` |
| `utf8` encoding meaning | WITH BOM | WITHOUT BOM | Always use `utf8NoBOM` explicitly |
| `$PSNativeCommandUseErrorActionPreference` | ✗ | ✓ (PS7.3+) | Always check `$LASTEXITCODE` manually |

### File encoding — the PS5.1 / PS7+ trap

```powershell
# In PS5.1: -Encoding utf8 writes UTF-8 WITH BOM (0xEF 0xBB 0xBF prefix)
# In PS7+:  -Encoding utf8 writes UTF-8 WITHOUT BOM
# This silently breaks files consumed by tools that hate BOM (Linux, JSON parsers, etc.)

# Always use utf8NoBOM to be explicit and portable:
$content | Out-File -FilePath $path -Encoding utf8NoBOM
Set-Content -Path $path -Value $content -Encoding utf8NoBOM
```

### Version-gating code

```powershell
if ($PSVersionTable.PSVersion.Major -ge 7) {
    # PS7+ specific code
} else {
    # PS5.1 fallback
}

# Cross-platform OS check (portable):
$isWindows = $Env:OS -eq 'Windows_NT' -or $PSVersionTable.Platform -eq 'Win32NT'
```

### `String.Split()` behaviour change

`String.Split()` treats its argument differently between .NET Framework (PS 5.1) and .NET 5+ (PS 7+):

```powershell
"1111p2222q3333".Split('pq')
# PS 5.1: Splits on 'p' AND 'q' (treated as char[]) → "1111", "2222", "3333"
# PS 7+:  Splits on literal string "pq" (treated as string) → "1111p2222q3333" (no split!)

# ✅ Portable: Explicitly cast to char[] for consistent multi-character splitting
"1111p2222q3333".Split([char[]]'pq')   # Same behaviour on both versions: "1111", "2222", "3333"
```

### `$IsWindows` portability

`$IsWindows` does not exist in PS 5.1 — it evaluates to `$null` (falsy). The portable pattern:

```powershell
# ✅ Portable: works on PS 5.1 (Desktop) and PS 7+ (Core/Windows)
if ($PSVersionTable.PSEdition -eq 'Desktop' -or $IsWindows) {
    $tempPath = $env:TEMP
}
elseif ($IsLinux -or $IsMacOS) {
    $tempPath = '/tmp'
}

# ❌ WRONG in PS 5.1 — $IsWindows is $null (falsy), so this always goes to else
if ($IsWindows) { ... }
```

### `Import-Module -UseWindowsPowerShell` (migration bridge only)

`Import-Module -UseWindowsPowerShell` (PS 7, Windows only) creates a background WinRM remoting session to a PS 5.1 process. **This introduces serialization overhead** — complex objects become deserialized `PSObject` instances with string-only properties and no methods.

Use this only as a temporary migration bridge, not a permanent solution.

### `ForEach-Object -Parallel` (PS7+ only)

```powershell
# $using: scope modifier is required to access outer variables in parallel blocks
$multiplier = 10
$results = 1..100 | ForEach-Object -Parallel {
    $_ * $using:multiplier   # $using: captures by value, not by reference
} -ThrottleLimit 10

# Modifications inside -Parallel do NOT propagate back to the outer scope
```

---

## Constrained Language Mode (CLM)

Enterprise environments using AppLocker or WDAC policies often run PowerShell in Constrained Language Mode. Many "best practice" patterns from FullLanguage mode break silently or with cryptic errors under CLM.

### Detect the current language mode

```powershell
$ExecutionContext.SessionState.LanguageMode
# Returns: FullLanguage | ConstrainedLanguage | RestrictedLanguage | NoLanguage
```

### What CLM blocks

| Blocked Pattern | Reason |
|---|---|
| `[SomeType]::new(...)` | Direct .NET constructors |
| `New-Object -TypeName SomeType` | Arbitrary type instantiation |
| `Add-Type` (any form) | Type compilation/loading |
| Method calls on unapproved types | Restricted method access |
| COM objects (`New-Object -ComObject`) | COM interop |

### What CLM allows

- `[PSCustomObject]@{...}` — always safe
- `[ordered]@{...}` — always safe
- Primitive type accelerators: `[int]`, `[string]`, `[bool]`, `[datetime]`, `[guid]`, `[timespan]`, `[version]`
- `[regex]` and `-match`, `-replace`, `-split`
- Core approved cmdlets (most `Get-*`, `Set-*`, `Write-*`, etc.)
- Standard array operations: `@()`, indexing, `-contains`, `-in`
- Property access (dot notation) on PSObjects and approved types

### CLM-safe alternatives for common patterns

```powershell
# ❌ CLM-UNSAFE: Generic List
$list = [System.Collections.Generic.List[PSObject]]::new()

# ✅ CLM-SAFE: Capture foreach output (also cleaner)
$list = foreach ($item in $source) {
    [PSCustomObject]@{ Name = $item.Name }
}

# ✅ CLM-SAFE: ArrayList (usually whitelisted)
$list = [System.Collections.ArrayList]::new()
[void]$list.Add($item)
```

```powershell
# ❌ CLM-UNSAFE: Add-Type + HttpUtility
Add-Type -AssemblyName System.Web
$safe = [System.Web.HttpUtility]::HtmlEncode($value)

# ✅ CLM-SAFE: Manual regex replace (covers all 5 HTML special chars)
$safe = $value -replace '&', '&amp;' -replace '<', '&lt;' -replace '>', '&gt;' `
               -replace '"', '&quot;' -replace "'", '&#39;'
```

```powershell
# ❌ CLM-UNSAFE: ErrorRecord constructor
$rec = [System.Management.Automation.ErrorRecord]::new($ex, 'Id', $cat, $target)

# ✅ CLM-SAFE: Write-Error with parameters
Write-Error -Message $ex.Message -Category $cat -ErrorId 'Id' -TargetObject $target
```

```powershell
# ❌ CLM-UNSAFE: Split-Path -LeafBase (PS7+) and [IO.Path]
[System.IO.Path]::GetFileNameWithoutExtension($path)

# ✅ CLM-SAFE: String manipulation
(Split-Path -Path $path -Leaf) -replace '\.[^.]+$', ''
```
