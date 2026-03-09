# API and Web Request Patterns

---

## Authentication with `Invoke-RestMethod`

PowerShell 6.0+ has built-in `-Authentication` with `Basic`, `Bearer`, and `OAuth` schemes.

**Critical rule:** `-Authentication` overrides any `Authorization` header in `-Headers` or `-WebSession`. Never specify both — the explicit `-Authentication` wins silently.

```powershell
# ✅ Built-in bearer authentication (PS 6.0+)
$token = Read-Host -AsSecureString -Prompt 'Enter API token'
Invoke-RestMethod -Uri $uri -Authentication Bearer -Token $token

# ❌ Manual Base64 encoding — fragile, exposes credentials, bypasses SecureString
$headers = @{
    Authorization = "Basic $([Convert]::ToBase64String(
        [Text.Encoding]::ASCII.GetBytes("$user`:$password")))"
}
Invoke-RestMethod -Uri $uri -Headers $headers
```

---

## Pagination

`-FollowRelLink` returns **nested arrays** (array-of-arrays) that must be flattened. Omitting `-MaximumFollowRelLink` can cause **infinite loops** with some APIs. For OData-style `nextLink`, use an explicit loop:

```powershell
# ✅ OData nextLink pagination
$uri        = 'https://api.example.com/v1/resources'
$allResults = [System.Collections.Generic.List[object]]::new()
do {
    $response = Invoke-RestMethod -Uri $uri -Authentication Bearer -Token $token
    $allResults.AddRange($response.value)
    $uri = $response.'@odata.nextLink'
} while ($uri)
```

---

## Rate Limiting and Retry

`-MaximumRetryCount` and `-RetryIntervalSec` are available in PS 6.0+.

**PS 7.x behaviour:** When the failure is HTTP 429 and the response includes a `Retry-After` header, the cmdlet uses that header value as the retry interval — even if `-RetryIntervalSec` is specified. For non-429 codes, the fixed `-RetryIntervalSec` value is used.

**Custom retry logic is still needed for:**
- Windows PowerShell 5.1 (parameters not available)
- Non-429 rate limiting (e.g., 503 with `Retry-After`)
- Exponential backoff (native retry uses fixed interval)

```powershell
function Invoke-RateLimitedApi {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Uri,

        [int]$MaxRetries = 5,

        [hashtable]$RestParams = @{}
    )

    $attempt = 0
    while ($true) {
        $attempt++
        $response = Invoke-RestMethod -Uri $Uri @RestParams `
            -SkipHttpErrorCheck `
            -StatusCodeVariable 'statusCode' `
            -ResponseHeadersVariable 'responseHeaders'

        if ([int]$statusCode -eq 429 -and $attempt -le $MaxRetries) {
            $retryAfter = if ($responseHeaders['Retry-After']) {
                [int]$responseHeaders['Retry-After'][0]
            }
            else {
                [math]::Pow(2, $attempt)   # Exponential backoff fallback
            }
            Write-Warning "Rate limited. Retry $attempt/$MaxRetries in ${retryAfter}s"
            Start-Sleep -Seconds $retryAfter
        }
        elseif ([int]$statusCode -ge 400) {
            throw "API request failed with status $statusCode"
        }
        else {
            return $response
        }
    }
}
```

**Note:** `-SkipHttpErrorCheck` and `-StatusCodeVariable` require PS 7.0+. For PS 5.1 compatibility, wrap `Invoke-RestMethod` in `try/catch` and inspect `$_.Exception.Response.StatusCode`.

---

## Non-Throwing Error Inspection (PS 7.0+)

```powershell
# -SkipHttpErrorCheck prevents exceptions on 4xx/5xx
# -StatusCodeVariable captures the HTTP status as an int
# -ResponseHeadersVariable captures response headers
$response = Invoke-RestMethod -Uri $uri `
    -SkipHttpErrorCheck `
    -StatusCodeVariable 'httpStatus' `
    -ResponseHeadersVariable 'httpHeaders'

if ([int]$httpStatus -eq 404) {
    Write-Warning "Resource not found"
    return $null
}
elseif ([int]$httpStatus -ge 500) {
    throw "Server error: $httpStatus"
}
```

---

## `ConvertTo-Json` Depth

`ConvertTo-Json` defaults to depth **2** in **both** Windows PowerShell 5.1 and PowerShell 7.x. At depth 2, nested objects beyond the second level are silently replaced with their type name string (e.g., `"System.Collections.Hashtable"`).

**Always specify `-Depth` explicitly:**

```powershell
# ✅ Always explicit
$body = $complexObject | ConvertTo-Json -Depth 10

# ❌ Silent data truncation at depth > 2
$body = $complexObject | ConvertTo-Json
```

**PS 7.1+ note:** Emits a warning when truncation occurs. PS 5.1 does not — truncation is completely silent.

---

## Credential Parameters

The standard triple-attribute decoration pattern for credential parameters:

```powershell
param(
    [Parameter()]
    [ValidateNotNull()]
    [System.Management.Automation.PSCredential]
    [System.Management.Automation.Credential()]
    $Credential = [System.Management.Automation.PSCredential]::Empty
)
```

### Storing credentials at rest

| Method | Scope | Security |
|---|---|---|
| `Export-Clixml` (no `-Key`) | Same user + same machine only | DPAPI encryption (Windows) |
| `ConvertFrom-SecureString -Key` | Cross-machine | AES; security shifts to key management |
| `Microsoft.PowerShell.SecretManagement` | Team/multi-machine | Vault-agnostic; requires installation |

**Cross-platform warning:** On non-Windows platforms, `SecureString` provides **no encryption**. `ConvertFrom-SecureString` and `Export-Clixml` produce hex-encoded plaintext. Microsoft has formally deprecated `SecureString` for new .NET Core development.

---

## PSReadLine: History Protection for Credentials

PSReadLine sensitive history filtering was introduced in **v2.0.0 GA** (February 2020). The version bundled with the original Windows PowerShell 5.1 release predates this — but PSReadLine is updated independently via Windows Update. Verify with `(Get-Module PSReadLine).Version`.

Always add an explicit handler for defence-in-depth:

```powershell
Set-PSReadLineOption -AddToHistoryHandler {
    param([string]$line)
    return ($line -notmatch 'password|asplaintext|token|apikey|secret|connectionstring')
}
```

---

## `$ProgressPreference` for Non-Interactive Scripts

`Invoke-WebRequest` and `Invoke-RestMethod` write to the Progress stream by default. In PS 5.1 this renders a progress bar that significantly slows output and clutters logs. Set at the script top:

```powershell
$ProgressPreference = 'SilentlyContinue'
```
