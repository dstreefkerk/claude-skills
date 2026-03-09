# Discovering PowerShell: Get-Help and Get-Member

Before writing code that uses an unfamiliar cmdlet or object, **always discover first**. PowerShell's built-in introspection tools eliminate guesswork about parameter names, property names, types, and usage patterns.

---

## Get-Help — Reading cmdlet documentation

### Core usage

```powershell
# Synopsis, description, and parameter list
Get-Help Get-ChildItem

# Full documentation including parameter details, input/output types, and notes
Get-Help Get-ChildItem -Full

# Just the examples — fastest way to understand real usage
Get-Help Get-ChildItem -Examples

# Details for a specific parameter
Get-Help Get-ChildItem -Parameter Filter

# Open the official Microsoft Docs page in the browser
Get-Help Get-ChildItem -Online

# Conceptual help topics (about_ topics cover language features, operators, etc.)
Get-Help about_Functions
Get-Help about_Regular_Expressions
Get-Help about_CommonParameters
```

### Keeping help current

Local help files are not installed by default on all systems and can be outdated. Update them before relying on offline docs:

```powershell
# Run as admin to update all installed help
Update-Help -Force

# Update help for a specific module only
Update-Help -Module Az.Accounts -Force
```

If `Get-Help` returns only auto-generated stubs (no description, no examples), run `Update-Help` or use `-Online` to read the current Microsoft Docs page.

### Discovering cmdlets and modules

```powershell
# Find cmdlets whose name matches a pattern
Get-Command -Name '*Network*'
Get-Command -Verb 'Get' -Noun 'Process'

# All cmdlets in a module
Get-Command -Module Az.Compute

# Which module provides a cmdlet
(Get-Command Get-ChildItem).Source
```

---

## Get-Member — Discovering object properties and methods

`Get-Member` reveals exactly what properties and methods an object exposes. Use it before writing dot-notation access to avoid guessing property names.

### Core usage

```powershell
# All members of whatever Get-Process returns
Get-Process | Get-Member

# Properties only — the ones you can read and write
Get-Process | Get-Member -MemberType Property

# Methods only — callable actions
Get-Process | Get-Member -MemberType Method

# NoteProperty members (added dynamically, common on PSCustomObjects and deserialized objects)
$result | Get-Member -MemberType NoteProperty

# Script properties (computed, common on objects returned by AD/CIM/WMI cmdlets)
Get-ADUser -Filter * | Get-Member -MemberType ScriptProperty

# Static members (class-level, called on the type itself not an instance)
[System.Math] | Get-Member -Static
[System.DateTime] | Get-Member -Static -MemberType Method
```

### Inspecting the TypeName

The TypeName at the top of `Get-Member` output tells you the exact .NET type — useful for casting, parameter type declarations, and looking up online docs.

```powershell
# Get-Member always shows the TypeName first:
#   TypeName: System.Diagnostics.Process
Get-Process | Get-Member | Select-Object -First 1

# Get the type directly on an instance:
$proc = Get-Process -Name explorer
$proc.GetType().FullName    # System.Diagnostics.Process
$proc.GetType().Name        # Process
```

### Listing all property values on an object

```powershell
# Expand all properties — useful when you don't know what data is there
Get-Process -Name explorer | Select-Object -Property *

# Nested objects: pipe the nested value into Get-Member or Select-Object *
$proc = Get-Process -Name explorer
$proc.MainModule | Select-Object -Property *
```

### Inspecting deserialized objects (PSRemoting, Import-Clixml)

Objects returned through `Invoke-Command` or imported from XML are **deserialized** — they lose their original methods. `Get-Member` will show `TypeName: Deserialized.System.Diagnostics.Process`. Only properties (as NoteProperty) are available; methods will not be present.

```powershell
$remoteProcs = Invoke-Command -ComputerName Server01 -ScriptBlock { Get-Process }
$remoteProcs | Get-Member   # TypeName: Deserialized.System.Diagnostics.Process
                             # Methods: absent — only NoteProperty members exist
```

---

## Practical workflow: before using an unfamiliar cmdlet

1. **Check parameters**: `Get-Help <Cmdlet> -Full` — confirm parameter names, types, mandatory/optional status, and pipeline binding.
2. **See examples**: `Get-Help <Cmdlet> -Examples` — understand real invocation patterns before writing your own.
3. **Inspect output**: `<Cmdlet> | Get-Member` — discover exactly what properties and methods the output objects have.
4. **Expand one result**: `<Cmdlet> | Select-Object *` — see actual property values on a real object.

```powershell
# Example: exploring Get-NetAdapter before writing code
Get-Help Get-NetAdapter -Examples
Get-NetAdapter | Get-Member -MemberType Property
Get-NetAdapter | Select-Object -Property *
```

---

## Online documentation and web search

### Get-Help -Online

`Get-Help -Online` opens the Microsoft Docs page for that cmdlet directly in the default browser. This is the fastest route to current, fully-rendered documentation with examples and community notes.

```powershell
Get-Help Invoke-RestMethod -Online
Get-Help Get-WinEvent -Online
Get-Help about_Splatting -Online
```

### Web search patterns for PowerShell documentation

When `-Online` fails, the local system has no browser, or you need documentation for a module not installed locally, use web search.

**Effective search patterns:**

| Goal | Search Query |
|---|---|
| Cmdlet reference | `Get-ChildItem PowerShell Microsoft Docs` |
| Specific parameter | `Invoke-RestMethod -Authentication PowerShell` |
| Module cmdlet | `Az.Storage Set-AzStorageBlobContent Microsoft Learn` |
| Conceptual topic | `PowerShell about_CommonParameters` |
| Error message | `PowerShell "The term 'X' is not recognized" fix` |

**Authoritative URLs to target in searches:**
- `learn.microsoft.com/powershell` — official Microsoft Learn docs
- `learn.microsoft.com/en-us/powershell/module/<module>/<cmdlet>` — cmdlet reference pages

**When to use web search over Get-Help:**
- Module not installed on the current machine (e.g., Az, ExchangeOnlineManagement)
- Need to see latest updates or version-specific notes
- Looking for community examples beyond the built-in help
- Cross-referencing parameter behaviour across PS5.1 and PS7+

---

## Quick reference card

| Task | Command |
|---|---|
| Cmdlet overview | `Get-Help <Cmdlet>` |
| Full docs + param types | `Get-Help <Cmdlet> -Full` |
| Usage examples | `Get-Help <Cmdlet> -Examples` |
| One parameter detail | `Get-Help <Cmdlet> -Parameter <Name>` |
| Open browser docs | `Get-Help <Cmdlet> -Online` |
| All object members | `$obj \| Get-Member` |
| Properties only | `$obj \| Get-Member -MemberType Property` |
| Methods only | `$obj \| Get-Member -MemberType Method` |
| All property values | `$obj \| Select-Object -Property *` |
| Object type name | `$obj.GetType().FullName` |
| Static members | `[TypeName] \| Get-Member -Static` |
| Cmdlets matching pattern | `Get-Command -Name '*Keyword*'` |
| All cmdlets in module | `Get-Command -Module <Module>` |
| Update offline help | `Update-Help -Force` (run as admin) |
