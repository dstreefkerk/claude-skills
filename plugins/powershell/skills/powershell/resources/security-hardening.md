# Security Hardening

---

## Execution Policy Is Not a Security Boundary

Microsoft's own documentation states explicitly: execution policy is a **safety feature** to prevent accidental script execution, not a defence against deliberate actors. It is trivially bypassed:

```powershell
pwsh.exe -ExecutionPolicy Bypass -File script.ps1
# Or: pipe script content to stdin, paste directly into console, etc.
```

**Never rely on execution policy as a security control.**

---

## Constrained Language Mode (CLM)

CLM is the actual PowerShell security boundary. It restricts .NET type access, blocks COM objects, prevents `Add-Type`, and disallows arbitrary type conversion.

CLM must be enforced by a system-wide application control policy:

- **WDAC (Windows Defender Application Control)** — Microsoft's preferred mechanism. Actively developed. Recommended for new deployments.
- **AppLocker** — Legacy. Microsoft states it is no longer receiving feature investment — security fixes only. Note: AppLocker CLM enforcement had a regression in Windows 11 24H2, fixed in May 2025 patches.

```powershell
# Check current language mode
$ExecutionContext.SessionState.LanguageMode
# Returns: FullLanguage | ConstrainedLanguage | RestrictedLanguage | NoLanguage
```

**Do not** attempt to set language mode via `$ExecutionContext.SessionState.LanguageMode` — it is not enforced and trivially bypassable. Only WDAC/AppLocker policy enforcement is authoritative.

See `compatibility-and-clm.md` for CLM-safe coding patterns.

---

## Three Complementary Logging Mechanisms

Mandiant recommends enabling all three — each captures different attack indicators:

| Mechanism | What It Captures | Event ID |
|---|---|---|
| **Module Logging** | Pipeline execution events | 4103 |
| **Script Block Logging** | Full script content before execution | 4104 |
| **Transcription** | Complete session I/O | N/A (files) |

Enable all three via Group Policy or WDAC policy. They are complementary, not redundant.

### Protected Event Logging

Adds CMS-based encryption to event log entries, preventing credential exposure in logs:
- The **public key** encrypts on the endpoint
- The **private key** decrypts on the SIEM

This prevents Script Block Logging from exposing credentials in plaintext in event logs — a significant risk when `$VerbosePreference` or debugging captures sensitive values.

---

## Script Injection Prevention

`Invoke-Expression` is a documented security hazard — PSScriptAnalyzer flags it with `AvoidUsingInvokeExpression`. The call operator `&` and splatting cover nearly all legitimate use cases:

```powershell
# ❌ Injection risk — $ProcId could contain: 1; Remove-Item C:\ -Recurse -Force
function Get-ProcessById {
    param($ProcId)
    Invoke-Expression "Get-Process -Id $ProcId"
}

# ✅ Typed parameter prevents injection — non-integer input is rejected at binding
function Get-ProcessById {
    [CmdletBinding()]
    param([int]$ProcId)   # Type constraint rejects non-integers
    Get-Process -Id $ProcId
}

# ✅ Splatting for dynamic parameter construction
$params = @{ ComputerName = $server; Name = 'W32Time' }
Get-Service @params
```

When `Invoke-Expression` is genuinely unavoidable, use the built-in escaping method:

```powershell
$safe = [System.Management.Automation.Language.CodeGeneration]::EscapeSingleQuotedStringContent($userInput)
```

---

## Code Signing

Script signing is built-in via the `Microsoft.PowerShell.Security` module (ships with all PS editions):

```powershell
# Find a valid code signing certificate
$cert = Get-ChildItem -Path Cert:\CurrentUser\My -CodeSigningCert |
    Where-Object { $_.NotAfter -gt (Get-Date) } |
    Select-Object -First 1

# Sign a script
Set-AuthenticodeSignature -FilePath '.\Deploy.ps1' `
    -Certificate $cert `
    -TimestampServer 'http://timestamp.digicert.com' `
    -HashAlgorithm SHA256

# Verify a signature
Get-AuthenticodeSignature -FilePath '.\Deploy.ps1'
```

---

## Just Enough Administration (JEA)

JEA implements native least-privilege remote administration via Role Capability files (`.psrc`) and Session Configuration files (`.pssc`):

```powershell
# Role capability: only allow restarting DNS service
New-PSRoleCapabilityFile -Path .\DnsAdminRole.psrc -VisibleCmdlets @(
    'Restart-Service'
    @{ Name = 'Get-Service'; Parameters = @{ Name = 'Name'; ValidateSet = 'DNS' } }
)

# Session configuration: virtual account, restricted language
New-PSSessionConfigurationFile -Path .\DnsEndpoint.pssc `
    -SessionType RestrictedRemoteServer `
    -RunAsVirtualAccount `
    -RoleDefinitions @{
        'CONTOSO\DnsAdmins' = @{ RoleCapabilities = 'DnsAdminRole' }
    } `
    -TranscriptDirectory 'C:\JEATranscripts'

Register-PSSessionConfiguration -Name 'DnsAdmin' -Path .\DnsEndpoint.pssc
```

### `-RunAsVirtualAccount` vs `-GroupManagedServiceAccount`

| Option | Network Access | Audit Trail |
|---|---|---|
| `-RunAsVirtualAccount` | **Cannot access network resources** (file shares, web services) | Per-session identity |
| `-GroupManagedServiceAccount` | Can access network resources | Shared identity — transcripts are essential for accountability |

Do not combine both options. If `RunAsVirtualAccount` is `$true`, the gMSA setting is ignored.

**Rule:** Use virtual accounts for local-only administration. Use gMSA when JEA sessions need to reach remote resources.

---

## Hardcoded Credentials

```powershell
# ❌ CRITICAL — exposed in source control and process listings
$password = 'P@ssw0rd!'
$securePass = ConvertTo-SecureString 'P@ssw0rd!' -AsPlainText -Force

# ✅ Interactive prompt — never stored
$securePass = Read-Host -AsSecureString -Prompt 'Enter password'

# ✅ SecretManagement vault (requires module)
$securePass = Get-Secret -Name 'MyServicePassword' -Vault 'LocalVault'

# ✅ Mandatory parameter — caller provides, nothing hardcoded
param(
    [Parameter(Mandatory)]
    [ValidateNotNull()]
    [System.Management.Automation.PSCredential]
    [System.Management.Automation.Credential()]
    $Credential
)
```

---

## CredSSP: Avoid

CredSSP delegates full credentials to the remote machine — the remote machine can use them to authenticate anywhere. Prefer Kerberos constrained delegation instead. If CredSSP is unavoidable, scope it narrowly and document the risk explicitly.

---

## Transcript Capture for Completeness

`Start-Transcript` has a known timing gap: objects formatted by `Out-Default` after `Stop-Transcript` is called can be lost. Wrap session content to ensure complete capture:

```powershell
Start-Transcript -Path "C:\Logs\session_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
. {
    # All session work inside this script block
    Get-Service | Where-Object { $_.Status -eq 'Stopped' }
} | Out-Default
Stop-Transcript
```

### Stream Redirection and Log Width

`*>` captures all six streams to a single file, but the file inherits console width — silently truncating wide tables. Set width explicitly:

```powershell
$PSDefaultParameterValues['Out-File:Width'] = 2000
.\Deploy-Application.ps1 *> C:\Logs\deploy.log
```
