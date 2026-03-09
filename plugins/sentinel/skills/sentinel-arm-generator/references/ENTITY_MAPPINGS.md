# Entity Mapping Reference

Entity extraction and mapping for Microsoft Sentinel analytic rules.

---

## Entity Type Reference

| Entity Type | Common Identifiers | Description |
|-------------|-------------------|-------------|
| Account | Name, FullName, AadUserId, Sid, UPNSuffix | User accounts |
| Host | HostName, DnsDomain, NetBiosName, AzureID | Computer systems |
| IP | Address | IP addresses |
| URL | Url | Web addresses |
| File | Name, Directory | Files |
| FileHash | Algorithm, Value | File hashes |
| Process | ProcessId, CommandLine, ElevationToken | Running processes |
| RegistryKey | Hive, Key | Windows registry keys |
| RegistryValue | Name, Value | Registry values |
| Mailbox | MailboxPrimaryAddress, DisplayName | Email mailboxes |
| CloudApplication | AppId, Name | Cloud applications |
| AzureResource | ResourceId | Azure resources |
| DNS | DomainName | DNS records |

---

## Strong vs Weak Identifiers

**Strong Identifiers** (preferred - enable better entity correlation):
- Account: `AadUserId`, `Sid`
- Host: `AzureID`, `DnsDomain`

**Weak Identifiers** (use when strong not available):
- Account: `FullName`, `Name`, `UPNSuffix`
- Host: `HostName`, `NetBiosName`

---

## Column Name Patterns

### Account Entities
| Column Pattern | Maps To |
|----------------|---------|
| UserPrincipalName | Account.FullName |
| AccountName, TargetUserName | Account.Name |
| InitiatingProcessAccountName | Account.Name |
| AccountObjectId, AadUserId | Account.AadUserId |
| AccountSid | Account.Sid |

### IP Entities
| Column Pattern | Maps To |
|----------------|---------|
| IPAddress, SourceIP, ClientIP | IP.Address |
| DestinationIP, RemoteIP | IP.Address |

### Host Entities
| Column Pattern | Maps To |
|----------------|---------|
| DeviceName, ComputerName | Host.HostName |
| Computer, HostName | Host.HostName |

### Process Entities
| Column Pattern | Maps To |
|----------------|---------|
| ProcessName, ProcessFileName | Process.ProcessId |
| InitiatingProcessFileName | Process.ProcessId |
| ProcessCommandLine, CommandLine | Process.CommandLine |

### File Entities
| Column Pattern | Maps To |
|----------------|---------|
| FileName | File.Name |
| FilePath, FolderPath | File.Directory |
| FileHash, SHA256 | FileHash.Value |

### URL Entities
| Column Pattern | Maps To |
|----------------|---------|
| Url, FileOriginUrl, RemoteUrl | URL.Url |

### Registry Entities
| Column Pattern | Maps To |
|----------------|---------|
| RegistryKey | RegistryKey.Key |
| RegistryValueName | RegistryValue.Name |

---

## ARM Template Entity Structure

```json
"entityMappings": [
  {
    "entityType": "Account",
    "fieldMappings": [
      { "identifier": "FullName", "columnName": "UserPrincipalName" }
    ]
  },
  {
    "entityType": "IP",
    "fieldMappings": [
      { "identifier": "Address", "columnName": "IPAddress" }
    ]
  },
  {
    "entityType": "Host",
    "fieldMappings": [
      { "identifier": "HostName", "columnName": "DeviceName" }
    ]
  }
]
```

---

## Constraints

- **Maximum 5 entity mappings** per rule
- **Each entity type can only be mapped once**
- Column names must match KQL output exactly (case-sensitive)
- Field mappings must reference columns that exist in query output
