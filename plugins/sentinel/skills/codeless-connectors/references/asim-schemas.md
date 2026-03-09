# ASIM Schema Reference

Advanced Security Information Model (ASIM) normalization schemas for Microsoft Sentinel. Use these when building connectors that target ASIM destination tables.

Source: https://learn.microsoft.com/azure/sentinel/normalization-about-schemas

---

## ASIM Destination Tables

| Schema | Destination Table | Unifying Parser |
|--------|------------------|-----------------|
| Audit Event | `ASimAuditEventLogs` | `_Im_AuditEvent` |
| Authentication Event | `ASimAuthenticationEventLogs` | `_Im_Authentication` |
| DNS Activity | `ASimDnsActivityLogs` | `_Im_Dns` |
| DHCP Activity | `ASimDhcpEventLogs` | `_Im_DhcpEvent` |
| File Event | `ASimFileEventLogs` | `_Im_FileEvent` |
| Network Session | `ASimNetworkSessionLogs` | `_Im_NetworkSession` |
| Process Event | `ASimProcessEventLogs` | `_Im_ProcessCreate` / `_Im_ProcessTerminate` |
| Registry Event | `ASimRegistryEventLogs` | `_Im_RegistryEvent` |
| User Management | `ASimUserManagementActivityLogs` | `_Im_UserManagement` |
| Web Session | `ASimWebSessionLogs` | `_Im_WebSession` |

For ingest-time normalization via DCR, use the `Microsoft-` prefixed output stream name (e.g., `Microsoft-ASimNetworkSessionLogs`).

---

## Common Event Fields (All Schemas)

These fields appear in every ASIM schema.

### Mandatory Common Fields

| Field | Type | Description |
|-------|------|-------------|
| `EventCount` | int | Number of events described by the record (usually `1`) |
| `EventStartTime` | datetime | Time the event started; aliases `TimeGenerated` if not provided |
| `EventEndTime` | datetime | Time the event ended; aliases `TimeGenerated` if not provided |
| `EventType` | string | Normalized operation type (schema-specific allowed values) |
| `EventResult` | string | `Success`, `Partial`, `Failure`, or `NA` |
| `EventProduct` | string | Product generating the event |
| `EventVendor` | string | Vendor of the product |
| `EventSchema` | string | Schema name (e.g., `Dns`, `Authentication`) |
| `EventSchemaVersion` | string | Schema version (e.g., `0.1.7`) |
| `Dvc` | string | Unique identifier of the reporting device |

### Recommended Common Fields

| Field | Type | Description |
|-------|------|-------------|
| `EventResultDetails` | string | Reason/details for `EventResult` |
| `EventSeverity` | string | `Informational`, `Low`, `Medium`, `High` |
| `EventUid` | string | Unique ID assigned by Sentinel (maps to `_ItemId`) |
| `DvcIpAddr` | string | IP address of the reporting device |
| `DvcHostname` | string | Hostname of the reporting device |
| `DvcDomain` | string | Domain of the reporting device |
| `DvcDomainType` | string | Type of `DvcDomain` (`Windows` or `FQDN`) |
| `DvcFQDN` | string | FQDN of the reporting device |
| `DvcId` | string | Unique ID of the reporting device |
| `DvcIdType` | string | Type of `DvcId` |
| `DvcAction` | string | Action taken by the reporting device |

### Optional Common Fields

| Field | Type | Description |
|-------|------|-------------|
| `EventMessage` | string | General message or description |
| `EventSubType` | string | Subdivision of `EventType` |
| `EventOriginalUid` | string | Original unique ID from source |
| `EventOriginalType` | string | Original event type/ID from source |
| `EventOriginalSubType` | string | Original event subtype from source |
| `EventOriginalResultDetails` | string | Original result details from source |
| `EventOriginalSeverity` | string | Original severity from source |
| `EventProductVersion` | string | Product version |
| `EventReportUrl` | string | URL to the event in the source product |
| `EventOwner` | string | Event owner |
| `AdditionalFields` | dynamic | Additional data not mapped to schema fields |

---

## Schema-Specific Fields

### 1. Audit Event

**Schema name:** `AuditEvent` | **Version:** `0.1.2` | **Table:** `ASimAuditEventLogs`

**EventType allowed values:** `Set`, `Read`, `Create`, `Delete`, `Execute`, `Install`, `Clear`, `Enable`, `Disable`, `Initialize`, `Start`, `Stop`, `Other`

| Field | Class | Type | Description |
|-------|-------|------|-------------|
| `Operation` | Mandatory | string | The operation audited as reported by the source |
| `Object` | Mandatory | string | Name of the object the operation was performed on |
| `ObjectId` | Optional | string | ID of the object |
| `ObjectType` | Conditional | string | Type: `Cloud Resource`, `Configuration Atom`, `Policy Rule`, `Event Log`, `Scheduled Task`, `Service`, `Directory Service Object`, `Other` |
| `OldValue` | Optional | string | Old value of object prior to operation |
| `NewValue` | Recommended | string | New value after operation |
| `Value` | Alias | | Alias to `NewValue` |
| `ValueType` | Conditional | string | Type of old/new values |
| `ActorUsername` | Recommended | string | The actor's username |
| `ActorUserId` | Optional | string | Machine-readable unique ID of the actor |
| `TargetAppName` | Optional | string | Application the event applies to |
| `Application` | Alias | | Alias to `TargetAppName` |

### 2. Authentication Event

**Schema name:** `Authentication` | **Version:** `0.1.4` | **Table:** `ASimAuthenticationEventLogs`

**EventType allowed values:** `Logon`, `Logoff`, `Elevate`

| Field | Class | Type | Description |
|-------|-------|------|-------------|
| `LogonMethod` | Optional | string | Method: `Managed Identity`, `Service Principal`, `Username & Password`, `Multi factor authentication`, `Passwordless`, `PKI`, `PAM`, `Other` |
| `LogonProtocol` | Optional | string | Protocol used (e.g., `NTLM`, `Kerberos`, `LDAP`) |
| `TargetUserId` | Optional | string | Machine-readable unique ID of target user |
| `TargetUsername` | Optional | string | Target user's username |
| `TargetUserType` | Optional | string | Type of target user |
| `TargetSessionId` | Optional | string | Sign-in session ID of target user |
| `ActorUsername` | Optional | string | Actor's username (if different from target) |
| `ActorUserId` | Optional | string | Machine-readable unique ID of actor |
| `LogonTarget` | Alias | | Alias to `TargetAppName`, `TargetUrl`, or `TargetHostname` |
| `User` | Alias | | Alias to `TargetUsername` |
| `SrcIpAddr` | Recommended | string | Source IP of the authentication attempt |
| `TargetAppName` | Optional | string | Application authenticated to |
| `TargetHostname` | Recommended | string | Target device hostname |
| `TargetDomain` | Recommended | string | Target device domain |

**EventSubType allowed values:** `System`, `Interactive`, `RemoteInteractive`, `Service`, `RemoteService`, `Remote`, `AssumeRole`

### 3. DNS Activity

**Schema name:** `Dns` | **Version:** `0.1.7` | **Table:** `ASimDnsActivityLogs`

**EventType allowed values:** DNS op codes (e.g., `Query`)

| Field | Class | Type | Description |
|-------|-------|------|-------------|
| `DnsQuery` | Mandatory | string | Domain being resolved (e.g., `www.example.com`) |
| `Domain` | Alias | | Alias to `DnsQuery` |
| `DnsQueryType` | Optional | int | DNS Resource Record Type code |
| `DnsQueryTypeName` | Recommended | string | DNS Resource Record Type name (e.g., `A`, `AAAA`, `CNAME`) |
| `DnsResponseName` | Optional | string | Content of the DNS response |
| `DnsResponseCode` | Optional | int | Numerical DNS response code |
| `DnsResponseCodeName` | Alias | | Alias to `EventResultDetails` |
| `TransactionIdHex` | Recommended | string | DNS query unique ID (hex) |
| `NetworkProtocol` | Optional | string | `UDP` or `TCP` |
| `DnsQueryClassName` | Recommended | string | DNS class name (usually `IN`) |
| `DnsNetworkDuration` | Optional | int | Time in milliseconds for DNS request completion |
| `DnsSessionId` | Optional | string | DNS session identifier |
| `SrcIpAddr` | Recommended | string | Client IP that sent the DNS request |
| `SrcHostname` | Recommended | string | Source device hostname |

**EventResultDetails:** DNS response code name (e.g., `NOERROR`, `NXDOMAIN`, `SERVFAIL`)

### 4. DHCP Activity

**Schema name:** `DhcpEvent` | **Version:** `0.1.1` | **Table:** `ASimDhcpEventLogs`

**EventType allowed values:** `Assign`, `Renew`, `Release`, `DNS Update`

| Field | Class | Type | Description |
|-------|-------|------|-------------|
| `SrcMacAddr` | Mandatory | string | MAC address of the DHCP client |
| `SrcHostname` | Recommended | string | Hostname of the DHCP client |
| `DhcpLeaseDuration` | Optional | int | Length of the DHCP lease in seconds |
| `DhcpSessionId` | Optional | string | Session identifier for the DHCP transaction |
| `DhcpSrcDHCId` | Optional | string | DHCP client ID (RFC 4701) |
| `RequestedIpAddr` | Optional | string | IP address requested by client |
| `SrcIpAddr` | Recommended | string | IP address assigned to client |
| `DhcpSessionDuration` | Optional | int | Duration of the DHCP session in seconds |
| `DhcpSrcDHCId` | Optional | string | DHCP Client Hardware Address |

### 5. File Event

**Schema name:** `FileEvent` | **Version:** `0.2.2` | **Table:** `ASimFileEventLogs`

**EventType allowed values:** `FileCreated`, `FileModified`, `FileDeleted`, `FileRenamed`, `FileCopied`, `FileMoved`, `FolderCreated`, `FolderDeleted`, `FolderRenamed`, `FolderMoved`, `FileAccessed`

| Field | Class | Type | Description |
|-------|-------|------|-------------|
| `TargetFilePath` | Mandatory | string | Full path to the target file |
| `TargetFilePathType` | Mandatory | string | Type of path: `Windows Local`, `Windows Share`, `Unix`, `URL` |
| `TargetFileName` | Recommended | string | Name of the target file |
| `TargetFileExtension` | Optional | string | Target file extension (e.g., `exe`) |
| `TargetFileMD5` | Optional | string | MD5 hash of the target file |
| `TargetFileSHA1` | Optional | string | SHA1 hash |
| `TargetFileSHA256` | Optional | string | SHA256 hash |
| `TargetFileSHA512` | Optional | string | SHA512 hash |
| `TargetFileSize` | Optional | long | Size in bytes |
| `SrcFilePath` | Optional | string | Source file path (for rename/copy/move) |
| `SrcFileName` | Optional | string | Source file name |
| `SrcFilePathType` | Optional | string | Type of source path |
| `Hash` | Alias | | Alias to best available hash field |
| `HashType` | Recommended | string | Type of hash in `Hash` field |
| `ActorUsername` | Recommended | string | User who performed the file operation |
| `ActingProcessName` | Optional | string | Process that performed the operation |
| `ActingProcessId` | Optional | string | Process ID |

### 6. Network Session

**Schema name:** `NetworkSession` | **Version:** `0.2.7` | **Table:** `ASimNetworkSessionLogs`

**EventType allowed values:** `NetworkSession`, `L2NetworkSession`, `Flow`, `EndpointNetworkSession`, `HTTPsession`

| Field | Class | Type | Description |
|-------|-------|------|-------------|
| `NetworkApplicationProtocol` | Optional | string | Application layer protocol (e.g., `HTTP`, `HTTPS`, `DNS`, `SSH`) |
| `NetworkProtocol` | Optional | string | Transport protocol (e.g., `TCP`, `UDP`, `ICMP`) |
| `NetworkProtocolVersion` | Optional | string | `IPv4` or `IPv6` |
| `NetworkDirection` | Optional | string | `Inbound`, `Outbound`, `Local`, `Listen` |
| `DstBytes` | Recommended | long | Bytes sent from destination to source |
| `SrcBytes` | Recommended | long | Bytes sent from source to destination |
| `NetworkBytes` | Optional | long | Total bytes in both directions |
| `DstPackets` | Optional | long | Packets from destination to source |
| `SrcPackets` | Optional | long | Packets from source to destination |
| `NetworkPackets` | Optional | long | Total packets |
| `NetworkSessionId` | Optional | string | Session identifier |
| `NetworkDuration` | Optional | int | Duration in milliseconds |
| `SrcIpAddr` | Recommended | string | Source IP address |
| `DstIpAddr` | Recommended | string | Destination IP address |
| `SrcPortNumber` | Optional | int | Source port |
| `DstPortNumber` | Optional | int | Destination port |
| `SrcHostname` | Recommended | string | Source device hostname |
| `DstHostname` | Recommended | string | Destination device hostname |
| `TcpFlagsIn` | Optional | int | TCP flags from destination to source |
| `TcpFlagsOut` | Optional | int | TCP flags from source to destination |

### 7. Process Event

**Schema name:** `ProcessEvent` | **Version:** `0.1.4` | **Table:** `ASimProcessEventLogs`

**EventType allowed values:** `ProcessCreated`, `ProcessTerminated`

| Field | Class | Type | Description |
|-------|-------|------|-------------|
| `ActorUsername` | Mandatory | string | Username who initiated the process event |
| `ActorUserId` | Recommended | string | Machine-readable unique ID of actor |
| `ActingProcessId` | Mandatory | string | Process ID of the acting (parent) process |
| `ActingProcessName` | Optional | string | Name of the acting process |
| `ActingProcessCommandLine` | Optional | string | Command line of the acting process |
| `TargetProcessName` | Mandatory | string | Name of the target process |
| `TargetProcessCommandLine` | Recommended | string | Command line of the target process |
| `TargetProcessId` | Mandatory | string | Process ID of the target process |
| `TargetProcessGuid` | Optional | string | GUID of the target process |
| `TargetProcessCreationTime` | Optional | datetime | When the target process was created |
| `TargetProcessMD5` | Optional | string | MD5 hash of the process image |
| `TargetProcessSHA1` | Optional | string | SHA1 hash |
| `TargetProcessSHA256` | Optional | string | SHA256 hash |
| `TargetProcessIntegrityLevel` | Optional | string | Integrity level (Windows) |
| `TargetProcessTokenElevation` | Optional | string | Token elevation type |
| `ParentProcessName` | Optional | string | Parent process name |

### 8. Registry Event

**Schema name:** `RegistryEvent` | **Version:** `0.1.3` | **Table:** `ASimRegistryEventLogs`

**EventType allowed values:** `RegistryKeyCreated`, `RegistryKeyDeleted`, `RegistryKeyRenamed`, `RegistryValueSet`, `RegistryValueDeleted`

| Field | Class | Type | Description |
|-------|-------|------|-------------|
| `RegistryKey` | Mandatory | string | Registry key associated with the operation (normalized to standard root key names) |
| `RegistryValue` | Conditional | string | Registry value name associated with the operation |
| `RegistryValueType` | Conditional | string | Type: `Reg_None`, `Reg_Sz`, `Reg_Expand_Sz`, `Reg_Binary`, `Reg_DWord`, `Reg_Multi_Sz`, `Reg_QWord` |
| `RegistryValueData` | Recommended | string | Data stored in the registry value |
| `RegistryPreviousKey` | Optional | string | Previous registry key (for rename operations) |
| `RegistryPreviousValue` | Optional | string | Previous registry value (for modifications) |
| `RegistryPreviousValueType` | Optional | string | Previous registry value type |
| `RegistryPreviousValueData` | Optional | string | Previous registry value data |
| `ActorUsername` | Mandatory | string | User who performed the operation |
| `ActorUserId` | Recommended | string | Machine-readable unique ID of actor |
| `ActingProcessName` | Optional | string | Process that performed the operation |
| `ActingProcessId` | Optional | string | Process ID |

### 9. User Management

**Schema name:** `UserManagement` | **Version:** `0.1.2` | **Table:** `ASimUserManagementActivityLogs`

**EventType allowed values:** `UserCreated`, `UserDeleted`, `UserModified`, `UserDisabled`, `UserEnabled`, `UserLocked`, `UserUnlocked`, `PasswordChanged`, `PasswordReset`, `GroupCreated`, `GroupDeleted`, `GroupModified`, `UserAddedToGroup`, `UserRemovedFromGroup`

| Field | Class | Type | Description |
|-------|-------|------|-------------|
| `UpdatedPropertyName` | Optional | string | Name of the property that was changed |
| `PreviousPropertyValue` | Optional | string | Previous value of the property |
| `NewPropertyValue` | Optional | string | New value of the property |
| `TargetUserId` | Recommended | string | Machine-readable unique ID of target user |
| `TargetUsername` | Mandatory | string | Username of the target user |
| `TargetUserType` | Optional | string | Type of target user |
| `GroupId` | Optional | string | Unique ID of the group (for group operations) |
| `GroupName` | Optional | string | Name of the group |
| `GroupType` | Optional | string | Type of group |
| `GroupOriginalType` | Optional | string | Original group type as reported |
| `ActorUsername` | Mandatory | string | User who performed the operation |
| `ActorUserId` | Recommended | string | Machine-readable unique ID of actor |
| `SrcIpAddr` | Recommended | string | Source IP of the management operation |

### 10. Web Session

**Schema name:** `WebSession` | **Version:** `0.2.7` | **Table:** `ASimWebSessionLogs`

**EventType allowed values:** `WebServerSession`, `WebProxySession`, `WebBrowserSession`, `HTTPsession`

| Field | Class | Type | Description |
|-------|-------|------|-------------|
| `Url` | Mandatory | string | Full HTTP request URL including parameters |
| `UrlCategory` | Optional | string | Category of the URL (e.g., `Search Engines`, `Adult`) |
| `HttpRequestMethod` | Recommended | string | HTTP method: `GET`, `POST`, `PUT`, `DELETE`, `HEAD`, `OPTIONS`, `TRACE`, `CONNECT`, `PATCH` |
| `HttpStatusCode` | Recommended | int | HTTP response status code (e.g., `200`, `404`) |
| `HttpContentType` | Optional | string | HTTP response content type header |
| `HttpContentFormat` | Optional | string | Content format part of content type |
| `HttpReferrer` | Optional | string | HTTP referrer header |
| `HttpUserAgent` | Optional | string | HTTP user agent header |
| `HttpRequestXff` | Optional | string | X-Forwarded-For header |
| `HttpRequestBody` | Optional | string | HTTP request body |
| `HttpResponseBody` | Optional | string | HTTP response body |
| `FileName` | Optional | string | File name transmitted over the connection |
| `FileMD5` | Optional | string | MD5 hash of transmitted file |
| `FileSHA1` | Optional | string | SHA1 hash |
| `FileSHA256` | Optional | string | SHA256 hash |
| `FileSize` | Optional | long | Size in bytes |
| `FileContentType` | Optional | string | Content type of transmitted file |
| `SrcIpAddr` | Recommended | string | Source IP address |
| `DstIpAddr` | Optional | string | Destination IP address |
| `DstPortNumber` | Optional | int | Destination port |
| `SrcHostname` | Recommended | string | Source device hostname |
| `DstHostname` | Optional | string | Destination device hostname |
| `NetworkBytes` | Optional | long | Total bytes |
| `NetworkDuration` | Optional | int | Session duration in milliseconds |

---

## Field Classes

| Class | Description |
|-------|-------------|
| **Mandatory** | Must appear in every parser. Missing mandatory fields mean the source can't be normalized. |
| **Recommended** | Should be normalized if available. Content items should account for these being absent. |
| **Optional** | Can be normalized or left in original form. Minimal parsers may skip for performance. |
| **Conditional** | Mandatory if the field they depend on is populated (e.g., `DvcIdType` is required if `DvcId` is set). |
| **Alias** | Points to another field. Mandatory if the aliased field is populated. |

---

## Using ASIM Schemas in DCR Transforms

When building an ingest-time normalization DCR, the `transformKql` must map source fields to the ASIM schema fields and the `outputStream` must reference the ASIM table:

```json
"dataFlows": [{
    "streams": ["Custom-RawVendorLogs"],
    "destinations": ["clv2ws1"],
    "transformKql": "source | extend TimeGenerated = todatetime(timestamp), EventType = 'Logon', EventResult = iif(status == 'success', 'Success', 'Failure'), EventProduct = 'VendorProduct', EventVendor = 'Vendor', EventSchema = 'Authentication', EventSchemaVersion = '0.1.4', EventCount = int(1), EventStartTime = todatetime(timestamp), EventEndTime = todatetime(timestamp), TargetUsername = username, SrcIpAddr = source_ip, LogonMethod = 'Username & Password', Dvc = hostname",
    "outputStream": "Microsoft-ASimAuthenticationEventLogs"
}]
```

Key rules:
- All mandatory fields for the chosen schema must be produced by the transform
- `EventSchema` must match the schema name exactly
- `EventSchemaVersion` should match the current version
- `TimeGenerated` is always required
- Use only supported KQL functions (see `reference/kql-transforms.md`)

## Microsoft Docs References

- ASIM Overview: https://learn.microsoft.com/azure/sentinel/normalization
- Schema Overview: https://learn.microsoft.com/azure/sentinel/normalization-about-schemas
- Common Fields: https://learn.microsoft.com/azure/sentinel/normalization-common-fields
- Audit Event: https://learn.microsoft.com/azure/sentinel/normalization-schema-audit
- Authentication: https://learn.microsoft.com/azure/sentinel/normalization-schema-authentication
- DNS Activity: https://learn.microsoft.com/azure/sentinel/normalization-schema-dns
- DHCP Activity: https://learn.microsoft.com/azure/sentinel/normalization-schema-dhcp
- File Event: https://learn.microsoft.com/azure/sentinel/normalization-schema-file-event
- Network Session: https://learn.microsoft.com/azure/sentinel/normalization-schema-network
- Process Event: https://learn.microsoft.com/azure/sentinel/normalization-schema-process-event
- Registry Event: https://learn.microsoft.com/azure/sentinel/normalization-schema-registry-event
- User Management: https://learn.microsoft.com/azure/sentinel/normalization-schema-user-management
- Web Session: https://learn.microsoft.com/azure/sentinel/normalization-schema-web
- Ingest-Time Normalization: https://learn.microsoft.com/azure/sentinel/normalization-ingest-time
