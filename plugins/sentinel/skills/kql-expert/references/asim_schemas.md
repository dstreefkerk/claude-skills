# ASIM (Advanced Security Information Model) Schema Reference

Comprehensive reference for Microsoft Sentinel's ASIM normalization layer.

## Overview

ASIM transforms proprietary source telemetry into a standardized format enabling source-agnostic detection rules. It aligns with the **Open Source Security Events Metadata (OSSEM)** common information model.

---

## Parser Types

| Type | Naming Convention | Use Case |
|------|-------------------|----------|
| **Unifying (with filtering)** | `_Im_<schema>` | Analytics rules (recommended) |
| **Source-specific (with filtering)** | `_Im_<schema>_<source>` | Source-specific workbooks |
| **Parameter-less (legacy)** | `_ASim_<schema>` | Avoid in production |
| **Workspace-deployed unifying** | `im<schema>` | Custom deployments |
| **Workspace-deployed source** | `vim<schema><source>` | Custom source parsers |

---

## Available Schemas

### Authentication Event

**Parser**: `_Im_Authentication`
**Native Table**: `ASimAuthenticationEventLogs`

**Common Parameters**:
- `starttime` (datetime): Start of time range
- `endtime` (datetime): End of time range
- `eventresult` (string): 'Success', 'Failure', 'NA'
- `eventtype` (string): 'Logon', 'Logoff', 'Elevate'
- `username_has_any` (dynamic): Filter by usernames
- `targetusername_has_any` (dynamic): Filter by target usernames
- `srcipaddr_has_any_prefix` (dynamic): Filter by source IP prefixes

**Key Columns**:
| Column | Type | Description |
|--------|------|-------------|
| TimeGenerated | datetime | Event timestamp |
| EventType | string | Logon, Logoff, Elevate |
| EventResult | string | Success, Failure, NA |
| EventResultDetails | string | Detailed result |
| TargetUsername | string | Target account name |
| TargetUserType | string | User type |
| SrcIpAddr | string | Source IP address |
| SrcHostname | string | Source hostname |
| LogonType | string | Interactive, Network, etc. |
| LogonMethod | string | Authentication method |

**Example**:
```kql
_Im_Authentication(
    starttime=ago(1h),
    endtime=now(),
    eventresult='Failure',
    username_has_any=dynamic(['admin', 'root'])
)
| summarize FailedAttempts = count() by TargetUsername, SrcIpAddr
| where FailedAttempts > 5
```

---

### Network Session

**Parser**: `_Im_NetworkSession`
**Native Table**: `ASimNetworkSessionLogs`

**Common Parameters**:
- `starttime` (datetime): Start of time range
- `endtime` (datetime): End of time range
- `srcipaddr_has_any_prefix` (dynamic): Source IP prefixes
- `dstipaddr_has_any_prefix` (dynamic): Destination IP prefixes
- `dstportnumber` (int): Destination port
- `hostname_has_any` (dynamic): Hostname filter
- `dvcaction` (string): Action taken

**Key Columns**:
| Column | Type | Description |
|--------|------|-------------|
| TimeGenerated | datetime | Event timestamp |
| SrcIpAddr | string | Source IP |
| DstIpAddr | string | Destination IP |
| DstPortNumber | int | Destination port |
| NetworkProtocol | string | TCP, UDP, etc. |
| NetworkDirection | string | Inbound, Outbound |
| SrcBytes | long | Bytes sent |
| DstBytes | long | Bytes received |
| NetworkDuration | int | Duration in ms |
| DvcAction | string | Allow, Deny, Drop |

**Example**:
```kql
_Im_NetworkSession(
    starttime=ago(1d),
    endtime=now(),
    dstportnumber=443,
    srcipaddr_has_any_prefix=dynamic(['10.0.', '192.168.'])
)
| summarize TotalBytes = sum(SrcBytes + DstBytes) by DstIpAddr
| top 10 by TotalBytes
```

---

### DNS Activity

**Parser**: `_Im_Dns`
**Native Table**: `ASimDnsActivityLogs`

**Common Parameters**:
- `starttime` (datetime): Start of time range
- `endtime` (datetime): End of time range
- `responsecodename` (string): 'NOERROR', 'NXDOMAIN', etc.
- `domain_has_any` (dynamic): Domain filter
- `srcipaddr_has_any_prefix` (dynamic): Source IP prefixes

**Key Columns**:
| Column | Type | Description |
|--------|------|-------------|
| TimeGenerated | datetime | Event timestamp |
| SrcIpAddr | string | Requesting IP |
| DnsQuery | string | Query domain |
| DnsQueryType | string | A, AAAA, CNAME, MX |
| DnsResponseCode | int | Response code |
| ResponseCodeName | string | NOERROR, NXDOMAIN |
| DnsResponseName | string | Resolved name |

**Example**:
```kql
_Im_Dns(
    starttime=ago(1h),
    endtime=now(),
    responsecodename='NXDOMAIN'
)
| summarize NXDomainCount = count() by SrcIpAddr, DnsQuery
| where NXDomainCount > 100
```

---

### Process Event

**Parser**: `_Im_ProcessEvent`
**Native Table**: `ASimProcessEventLogs`

**Common Parameters**:
- `starttime` (datetime): Start of time range
- `endtime` (datetime): End of time range
- `eventtype` (string): 'ProcessCreated', 'ProcessTerminated'
- `hostname_has_any` (dynamic): Hostname filter
- `commandline_has_any` (dynamic): Command line filter
- `commandline_has_all` (dynamic): All terms must match
- `actorusername_has_any` (dynamic): Actor username filter

**Key Columns**:
| Column | Type | Description |
|--------|------|-------------|
| TimeGenerated | datetime | Event timestamp |
| EventType | string | ProcessCreated, ProcessTerminated |
| DvcHostname | string | Device hostname |
| ActorUsername | string | User executing process |
| TargetProcessName | string | Process name |
| TargetProcessCommandLine | string | Full command line |
| TargetProcessId | string | Process ID |
| ParentProcessName | string | Parent process name |
| ParentProcessCommandLine | string | Parent command line |
| TargetProcessSHA256 | string | SHA256 hash |

**Example**:
```kql
_Im_ProcessEvent(
    starttime=ago(1h),
    endtime=now(),
    eventtype='ProcessCreated',
    commandline_has_any=dynamic(['powershell', 'cmd'])
)
| where TargetProcessCommandLine has_any ('IEX', 'Invoke-Expression', 'DownloadString')
| project TimeGenerated, DvcHostname, ActorUsername, TargetProcessCommandLine
```

---

### File Event

**Parser**: `_Im_FileEvent`
**Native Table**: `ASimFileEventLogs`

**Common Parameters**:
- `starttime` (datetime): Start of time range
- `endtime` (datetime): End of time range
- `eventtype` (string): 'FileCreated', 'FileModified', 'FileDeleted', 'FileRenamed'
- `filename_has_any` (dynamic): Filename filter
- `filepath_has_any` (dynamic): File path filter
- `srcfilepath_has_any` (dynamic): Source path filter

**Key Columns**:
| Column | Type | Description |
|--------|------|-------------|
| TimeGenerated | datetime | Event timestamp |
| EventType | string | FileCreated, FileModified, etc. |
| DvcHostname | string | Device hostname |
| ActorUsername | string | User performing action |
| TargetFileName | string | File name |
| TargetFilePath | string | Full file path |
| TargetFileSHA256 | string | File hash |
| TargetFileSize | long | File size in bytes |

---

### Registry Event

**Parser**: `_Im_RegistryEvent`
**Native Table**: `ASimRegistryEventLogs`

**Common Parameters**:
- `starttime` (datetime): Start of time range
- `endtime` (datetime): End of time range
- `eventtype` (string): 'RegistryKeyCreated', 'RegistryValueSet', etc.
- `registrykey_has_any` (dynamic): Registry key filter

**Key Columns**:
| Column | Type | Description |
|--------|------|-------------|
| TimeGenerated | datetime | Event timestamp |
| EventType | string | RegistryKeyCreated, RegistryValueSet |
| DvcHostname | string | Device hostname |
| ActorUsername | string | User making change |
| RegistryKey | string | Registry key path |
| RegistryValueName | string | Value name |
| RegistryValueData | string | Value data |
| RegistryPreviousValueData | string | Previous value |

---

### Web Session

**Parser**: `_Im_WebSession`
**Native Table**: `ASimWebSessionLogs`

**Common Parameters**:
- `starttime` (datetime): Start of time range
- `endtime` (datetime): End of time range
- `url_has_any` (dynamic): URL filter
- `srcipaddr_has_any_prefix` (dynamic): Source IP filter
- `httpuseragent_has_any` (dynamic): User agent filter

**Key Columns**:
| Column | Type | Description |
|--------|------|-------------|
| TimeGenerated | datetime | Event timestamp |
| SrcIpAddr | string | Source IP |
| Url | string | Full URL |
| UrlCategory | string | URL category |
| HttpRequestMethod | string | GET, POST, etc. |
| HttpStatusCode | int | Response code |
| HttpUserAgent | string | Browser/client |
| HttpRequestBodyBytes | long | Request size |
| HttpResponseBodyBytes | long | Response size |

---

### Audit Event

**Parser**: `_Im_AuditEvent`
**Native Table**: `ASimAuditEventLogs`

**Common Parameters**:
- `starttime` (datetime): Start of time range
- `endtime` (datetime): End of time range
- `eventtype` (string): Event type filter
- `operation_has_any` (dynamic): Operation filter
- `actorusername_has_any` (dynamic): Actor filter

**Key Columns**:
| Column | Type | Description |
|--------|------|-------------|
| TimeGenerated | datetime | Event timestamp |
| EventType | string | Type of audit event |
| Operation | string | Operation performed |
| ActorUsername | string | User performing action |
| Object | string | Object affected |
| ObjectType | string | Type of object |
| EventResult | string | Success/Failure |

---

### User Management

**Parser**: `_Im_UserManagement`
**Native Table**: `ASimUserManagementActivityLogs`

**Common Parameters**:
- `starttime` (datetime): Start of time range
- `endtime` (datetime): End of time range
- `eventtype` (string): 'UserCreated', 'UserModified', 'UserDeleted', 'UserDisabled'
- `targetusername_has_any` (dynamic): Target user filter
- `actorusername_has_any` (dynamic): Actor filter

---

### DHCP Activity

**Parser**: `_Im_Dhcp`
**Native Table**: `ASimDhcpEventLogs`

**Common Parameters**:
- `starttime` (datetime): Start of time range
- `endtime` (datetime): End of time range
- `srcipaddr_has_any_prefix` (dynamic): Source IP filter
- `srchostname_has_any` (dynamic): Hostname filter

---

### Alert Event

**Parser**: `_Im_AlertEvent`
**Native Table**: N/A (aggregates from various sources)

**Common Parameters**:
- `starttime` (datetime): Start of time range
- `endtime` (datetime): End of time range

---

## Best Practices

### Always Pass Filtering Parameters

```kql
// BAD - Scans all data, then filters
_Im_Authentication
| where TimeGenerated > ago(1h)
| where EventResult == 'Failure'

// GOOD - Filters pushed to source tables
_Im_Authentication(
    starttime=ago(1h),
    endtime=now(),
    eventresult='Failure'
)
```

### Why Filtering Parameters Matter

When you pass parameters to an ASIM parser:
1. The unifying parser passes filters to each source-specific parser
2. Source parsers push filters to native tables
3. Filtering occurs BEFORE normalization
4. Significantly reduces data processed

Without parameters:
1. All data from all sources is normalized
2. Only then are filters applied
3. Much higher resource consumption

### Use Unifying Parsers for Analytics Rules

```kql
// Detects brute force across ALL authentication sources
_Im_Authentication(
    starttime=ago(1h),
    endtime=now(),
    eventresult='Failure'
)
| summarize FailedAttempts = count() by SrcIpAddr, TargetUsername
| where FailedAttempts > 10
```

### Use Source-Specific Parsers for Workbooks

```kql
// Azure AD specific workbook
_Im_Authentication_AADSigninLogs(starttime=ago(7d))
| summarize count() by ResultType
| render piechart
```

---

## Performance Considerations

### Query-Time vs Ingest-Time Parsing

| Approach | Pros | Cons | Use When |
|----------|------|------|----------|
| Query-time | Preserves original data | Can slow queries | Default; smaller datasets |
| Ingest-time | Better performance | Less flexible | High-volume sources |
| Native tables | Best performance | Requires configuration | Production environments |

### Optimize with Specific Parameters

```kql
// More specific = faster
_Im_NetworkSession(
    starttime=ago(1h),
    endtime=now(),
    srcipaddr_has_any_prefix=dynamic(['10.0.0.']),  // Specific prefix
    dstportnumber=443                                // Specific port
)

// Less specific = slower
_Im_NetworkSession(
    starttime=ago(1h),
    endtime=now()
)
| where SrcIpAddr startswith "10.0.0."
| where DstPortNumber == 443
```

---

## Schema Mapping from CIM

| Splunk CIM Field | ASIM Field |
|------------------|------------|
| `src_ip` | `SrcIpAddr` |
| `dest_ip` | `DstIpAddr` |
| `src_port` | `SrcPortNumber` |
| `dest_port` | `DstPortNumber` |
| `user` | `ActorUsername` / `TargetUsername` |
| `action` | `EventType` / `DvcAction` |
| `signature` | `RuleName` |
| `file_name` | `TargetFileName` |
| `file_path` | `TargetFilePath` |
| `file_hash` | `TargetFileSHA256` |
| `process` | `TargetProcessName` |
| `parent_process` | `ParentProcessName` |
| `command_line` | `TargetProcessCommandLine` |

---

## References

- [Microsoft Learn - ASIM Overview](https://learn.microsoft.com/en-us/azure/sentinel/normalization)
- [Microsoft Learn - ASIM Schemas](https://learn.microsoft.com/en-us/azure/sentinel/normalization-about-schemas)
- [Microsoft Learn - ASIM Parsers](https://learn.microsoft.com/en-us/azure/sentinel/normalization-about-parsers)
- [OSSEM Project](https://ossemproject.com/)
