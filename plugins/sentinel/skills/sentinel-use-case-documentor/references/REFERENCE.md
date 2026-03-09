# Technical Reference: Sentinel Use Case Documentor

Comprehensive technical documentation for parsing ARM templates, analyzing KQL queries, and generating SOC use case documentation.

---

## Table of Contents

1. [ARM Template Structure](#arm-template-structure)
2. [Field Extraction Map](#field-extraction-map)
3. [KQL Query Analysis](#kql-query-analysis)
4. [Data Source Mappings](#data-source-mappings)
5. [MITRE ATT&CK Mappings](#mitre-attck-mappings)
6. [Inference Rules](#inference-rules)
7. [ISO 8601 Duration Parsing](#iso-8601-duration-parsing)
8. [Entity Mapping Reference](#entity-mapping-reference)

---

## ARM Template Structure

Sentinel analytics rules exported as ARM templates follow this structure:

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "workspace": {
      "type": "String"
    }
  },
  "resources": [
    {
      "id": "[concat(resourceId('Microsoft.OperationalInsights/workspaces/providers', parameters('workspace'), 'Microsoft.SecurityInsights'),'/alertRules/GUID-HERE')]",
      "name": "[concat(parameters('workspace'),'/Microsoft.SecurityInsights/GUID-HERE')]",
      "type": "Microsoft.OperationalInsights/workspaces/providers/alertRules",
      "kind": "Scheduled",
      "apiVersion": "2022-09-01-preview",
      "properties": {
        "displayName": "Rule Display Name",
        "description": "Rule description text",
        "severity": "Medium",
        "enabled": true,
        "query": "KQL query here",
        "queryFrequency": "PT30M",
        "queryPeriod": "P14D",
        "triggerOperator": "GreaterThan",
        "triggerThreshold": 0,
        "suppressionDuration": "PT5H",
        "suppressionEnabled": false,
        "tactics": ["Persistence"],
        "techniques": ["T1543"],
        "subTechniques": ["T1543.003"],
        "alertRuleTemplateName": null,
        "incidentConfiguration": {
          "createIncident": true,
          "groupingConfiguration": {
            "enabled": false,
            "reopenClosedIncident": false,
            "lookbackDuration": "PT5H",
            "matchingMethod": "AllEntities",
            "groupByEntities": [],
            "groupByAlertDetails": [],
            "groupByCustomDetails": []
          }
        },
        "eventGroupingSettings": {
          "aggregationKind": "SingleAlert"
        },
        "alertDetailsOverride": null,
        "customDetails": null,
        "entityMappings": [
          {
            "entityType": "Host",
            "fieldMappings": [
              {
                "identifier": "HostName",
                "columnName": "DeviceName"
              }
            ]
          },
          {
            "entityType": "Account",
            "fieldMappings": [
              {
                "identifier": "Name",
                "columnName": "AccountName"
              }
            ]
          }
        ],
        "sentinelEntitiesMappings": null
      }
    }
  ]
}
```

---

## Field Extraction Map

| Output Field | JSON Path | Notes |
|--------------|-----------|-------|
| Display Name | `resources[0].properties.displayName` | Rule name shown in Sentinel |
| Description | `resources[0].properties.description` | May contain author, URLs |
| Severity | `resources[0].properties.severity` | Informational, Low, Medium, High |
| Query | `resources[0].properties.query` | KQL detection logic |
| Query Frequency | `resources[0].properties.queryFrequency` | ISO 8601 duration |
| Query Period | `resources[0].properties.queryPeriod` | ISO 8601 duration (lookback) |
| Trigger Operator | `resources[0].properties.triggerOperator` | GreaterThan, LessThan, Equal, NotEqual |
| Trigger Threshold | `resources[0].properties.triggerThreshold` | Numeric threshold |
| Tactics | `resources[0].properties.tactics[]` | MITRE ATT&CK tactics |
| Techniques | `resources[0].properties.techniques[]` | MITRE technique IDs (T1xxx) |
| Sub-techniques | `resources[0].properties.subTechniques[]` | MITRE sub-technique IDs (T1xxx.xxx) |
| Entity Mappings | `resources[0].properties.entityMappings[]` | Alert enrichment fields |
| Rule GUID | Extract from `resources[0].id` | Last segment after `/alertRules/` |

### Extracting Rule GUID

```python
import re

def extract_rule_guid(resource_id):
    """Extract GUID from ARM template resource ID."""
    match = re.search(r'/alertRules/([a-f0-9-]+)', resource_id, re.IGNORECASE)
    return match.group(1) if match else None

# Example
resource_id = "[concat(resourceId(...),'/alertRules/12345678-1234-1234-1234-123456789abc')]"
guid = extract_rule_guid(resource_id)  # "12345678-1234-1234-1234-123456789abc"
```

### Extracting Author and URLs from Description

```python
import re

def extract_external_references(description):
    """Extract author and URLs from description field."""
    references = {
        'author': None,
        'urls': [],
        'clean_description': description
    }

    # Extract author patterns
    author_patterns = [
        r"Author:\s*([^\n,]+)",
        r"Created by:\s*([^\n,]+)",
        r"by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)"  # "by Firstname Lastname"
    ]

    for pattern in author_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            references['author'] = match.group(1).strip()
            break

    # Extract URLs
    url_pattern = r'https?://[^\s<>"\')]+[^\s<>"\').!,;:]'
    references['urls'] = re.findall(url_pattern, description)

    # Clean description (remove author line and URLs)
    clean = re.sub(r"Author:\s*[^\n]+\n?", "", description, flags=re.IGNORECASE)
    clean = re.sub(url_pattern, "", clean)
    references['clean_description'] = clean.strip()

    return references
```

---

## KQL Query Analysis

### Identifying Tables

Sentinel tables appear at the start of query lines or after `union`:

```python
SENTINEL_TABLES = {
    # Microsoft Defender for Endpoint
    'DeviceProcessEvents': {'connector': 'Microsoft Defender for Endpoint', 'category': 'Endpoint'},
    'DeviceNetworkEvents': {'connector': 'Microsoft Defender for Endpoint', 'category': 'Endpoint'},
    'DeviceFileEvents': {'connector': 'Microsoft Defender for Endpoint', 'category': 'Endpoint'},
    'DeviceImageLoadEvents': {'connector': 'Microsoft Defender for Endpoint', 'category': 'Endpoint'},
    'DeviceRegistryEvents': {'connector': 'Microsoft Defender for Endpoint', 'category': 'Endpoint'},
    'DeviceLogonEvents': {'connector': 'Microsoft Defender for Endpoint', 'category': 'Endpoint'},
    'DeviceEvents': {'connector': 'Microsoft Defender for Endpoint', 'category': 'Endpoint'},

    # Azure Active Directory
    'SigninLogs': {'connector': 'Azure Active Directory', 'category': 'Identity'},
    'AuditLogs': {'connector': 'Azure Active Directory', 'category': 'Identity'},
    'AADNonInteractiveUserSignInLogs': {'connector': 'Azure Active Directory', 'category': 'Identity'},
    'AADServicePrincipalSignInLogs': {'connector': 'Azure Active Directory', 'category': 'Identity'},
    'AADManagedIdentitySignInLogs': {'connector': 'Azure Active Directory', 'category': 'Identity'},
    'AADProvisioningLogs': {'connector': 'Azure Active Directory', 'category': 'Identity'},
    'AADRiskyUsers': {'connector': 'Azure AD Identity Protection', 'category': 'Identity'},
    'AADUserRiskEvents': {'connector': 'Azure AD Identity Protection', 'category': 'Identity'},

    # Windows Security Events
    'SecurityEvent': {'connector': 'Windows Security Events', 'category': 'Security'},
    'WindowsEvent': {'connector': 'Windows Security Events via AMA', 'category': 'Security'},

    # Office 365
    'OfficeActivity': {'connector': 'Office 365', 'category': 'Cloud Apps'},

    # Azure Activity
    'AzureActivity': {'connector': 'Azure Activity', 'category': 'Cloud'},
    'AzureDiagnostics': {'connector': 'Azure Diagnostics', 'category': 'Cloud'},

    # Security
    'CommonSecurityLog': {'connector': 'Common Event Format (CEF)', 'category': 'Security'},
    'Syslog': {'connector': 'Syslog', 'category': 'Linux'},
    'SecurityAlert': {'connector': 'Multiple', 'category': 'Security'},
    'SecurityIncident': {'connector': 'Microsoft Sentinel', 'category': 'Security'},

    # Threat Intelligence
    'ThreatIntelligenceIndicator': {'connector': 'Threat Intelligence', 'category': 'Threat Intel'},

    # DNS
    'DnsEvents': {'connector': 'DNS', 'category': 'Network'},

    # Network
    'AzureNetworkAnalytics_CL': {'connector': 'Azure Network Analytics', 'category': 'Network'},
}

def identify_tables(query):
    """Identify Sentinel tables used in KQL query."""
    tables_found = []

    for table_name, info in SENTINEL_TABLES.items():
        # Match table at start of line or after union/join
        pattern = rf'(?:^|\bunion\s+|\bjoin\s+)\s*{table_name}\b'
        if re.search(pattern, query, re.MULTILINE | re.IGNORECASE):
            tables_found.append({
                'table': table_name,
                'connector': info['connector'],
                'category': info['category']
            })

    return tables_found
```

### Extracting Thresholds

```python
def extract_thresholds(query):
    """Extract threshold conditions from KQL query."""
    thresholds = []

    patterns = [
        r'where\s+(\w+)\s*(>=|>|<=|<|==|!=)\s*(\d+)',
        r'(\w+)\s*(>=|>|<=|<|==|!=)\s*(\d+)',
        r'count\(\)\s*(>=|>|<=|<|==|!=)\s*(\d+)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, query, re.IGNORECASE)
        for match in matches:
            if len(match) == 3:
                thresholds.append({
                    'field': match[0],
                    'operator': match[1],
                    'value': int(match[2])
                })
            elif len(match) == 2:
                thresholds.append({
                    'field': 'count()',
                    'operator': match[0],
                    'value': int(match[1])
                })

    return thresholds
```

### Extracting Time Windows

```python
def extract_time_windows(query):
    """Extract time-related parameters from KQL query."""
    windows = []

    # bin() function
    bin_pattern = r'bin\s*\(\s*TimeGenerated\s*,\s*(\d+)([smhdw])\s*\)'
    for match in re.findall(bin_pattern, query, re.IGNORECASE):
        windows.append({
            'type': 'aggregation_bin',
            'value': int(match[0]),
            'unit': match[1]
        })

    # ago() function
    ago_pattern = r'ago\s*\(\s*(\d+)([smhdw])\s*\)'
    for match in re.findall(ago_pattern, query, re.IGNORECASE):
        windows.append({
            'type': 'lookback',
            'value': int(match[0]),
            'unit': match[1]
        })

    return windows
```

### Extracting Embedded Documentation

KQL queries may contain structured comments for SOC guidance:

```python
def extract_embedded_docs(query):
    """Extract structured documentation from KQL comments."""
    docs = {
        'description': None,
        'what_we_detect': None,
        'investigation_steps': None,
        'false_positives': None,
        'references': []
    }

    patterns = {
        'description': r'//\s*DESCRIPTION:\s*(.+?)(?=\n//|\n[^/]|$)',
        'what_we_detect': r'//\s*WHAT WE DETECT:\s*(.+?)(?=\n//|\n[^/]|$)',
        'investigation_steps': r'//\s*INVESTIGATION STEPS?:\s*(.+?)(?=\n//\s*[A-Z]|\n[^/]|$)',
        'false_positives': r'//\s*FALSE POSITIVES?:\s*(.+?)(?=\n//|\n[^/]|$)',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, query, re.IGNORECASE | re.DOTALL)
        if match:
            docs[key] = match.group(1).strip()

    return docs
```

---

## Data Source Mappings

### Complete Table-to-Connector Map

| Table | Connector | Ingestion Method | Category |
|-------|-----------|------------------|----------|
| SigninLogs | Azure Active Directory | Diagnostic Settings | Identity |
| AuditLogs | Azure Active Directory | Diagnostic Settings | Identity |
| AADNonInteractiveUserSignInLogs | Azure Active Directory | Diagnostic Settings | Identity |
| AADServicePrincipalSignInLogs | Azure Active Directory | Diagnostic Settings | Identity |
| AADManagedIdentitySignInLogs | Azure Active Directory | Diagnostic Settings | Identity |
| AADProvisioningLogs | Azure Active Directory | Diagnostic Settings | Identity |
| AADRiskyUsers | Azure AD Identity Protection | Diagnostic Settings | Identity |
| AADUserRiskEvents | Azure AD Identity Protection | Diagnostic Settings | Identity |
| SecurityEvent | Windows Security Events | MMA/AMA Agent | Security |
| WindowsEvent | Windows Security Events via AMA | Azure Monitor Agent | Security |
| DeviceProcessEvents | Microsoft Defender for Endpoint | M365 Defender Integration | Endpoint |
| DeviceNetworkEvents | Microsoft Defender for Endpoint | M365 Defender Integration | Endpoint |
| DeviceFileEvents | Microsoft Defender for Endpoint | M365 Defender Integration | Endpoint |
| DeviceImageLoadEvents | Microsoft Defender for Endpoint | M365 Defender Integration | Endpoint |
| DeviceRegistryEvents | Microsoft Defender for Endpoint | M365 Defender Integration | Endpoint |
| DeviceLogonEvents | Microsoft Defender for Endpoint | M365 Defender Integration | Endpoint |
| DeviceEvents | Microsoft Defender for Endpoint | M365 Defender Integration | Endpoint |
| OfficeActivity | Office 365 | Management API | Cloud Apps |
| AzureActivity | Azure Activity | Diagnostic Settings | Cloud |
| AzureDiagnostics | Azure Diagnostics | Diagnostic Settings | Cloud |
| CommonSecurityLog | CEF Sources | Syslog Forwarder | Security |
| Syslog | Linux/Unix | Syslog Agent | Linux |
| SecurityAlert | Multiple Sources | Various | Security |
| SecurityIncident | Microsoft Sentinel | Native | Security |
| ThreatIntelligenceIndicator | Threat Intelligence | TAXII/API | Threat Intel |
| DnsEvents | DNS | DNS Analytics | Network |

---

## MITRE ATT&CK Mappings

### Tactic to Kill Chain Phase

| Tactic | Kill Chain Phase | Description |
|--------|------------------|-------------|
| Reconnaissance | Reconnaissance | Gathering information about targets |
| ResourceDevelopment | Weaponization | Preparing attack infrastructure |
| InitialAccess | Delivery/Exploitation | Gaining initial foothold |
| Execution | Exploitation | Running malicious code |
| Persistence | Installation | Maintaining access |
| PrivilegeEscalation | Exploitation | Gaining higher privileges |
| DefenseEvasion | Actions on Objectives | Avoiding detection |
| CredentialAccess | Exploitation | Stealing credentials |
| Discovery | Actions on Objectives | Mapping the environment |
| LateralMovement | Actions on Objectives | Moving through network |
| Collection | Actions on Objectives | Gathering target data |
| CommandAndControl | Command & Control | Communicating with implants |
| Exfiltration | Actions on Objectives | Stealing data out |
| Impact | Actions on Objectives | Disrupting operations |

### Tactic to Problem Statement

| Tactic | Inferred Problem Statement |
|--------|---------------------------|
| Persistence | Attackers establishing persistence mechanisms to maintain long-term access to compromised systems |
| CredentialAccess | Credentials being harvested or stolen for unauthorized access to systems and data |
| InitialAccess | Unauthorized entry attempts to gain initial foothold in the environment |
| LateralMovement | Attackers moving laterally through the environment between systems |
| Exfiltration | Sensitive data being stolen and transferred out of the environment |
| Execution | Malicious code execution on compromised systems |
| PrivilegeEscalation | Attackers escalating privileges to gain administrative access |
| DefenseEvasion | Attackers evading security controls and detection mechanisms |
| Discovery | Attackers mapping the environment to identify targets and paths |
| Collection | Attackers collecting sensitive data for exfiltration |
| CommandAndControl | Attackers establishing command and control channels |
| Impact | Attackers disrupting operations or destroying data |

### Common Technique to Compliance Framework

| Technique | Compliance Frameworks |
|-----------|----------------------|
| T1543 (Create/Modify System Process) | NIST 800-53 CM-7, CIS Control 2.5 |
| T1543.003 (Windows Service) | NIST 800-53 CM-7, CIS Control 2.5, MITRE D3FEND |
| T1110 (Brute Force) | NIST 800-53 AC-7, PCI-DSS 8.1.6, CIS Control 4.4 |
| T1078 (Valid Accounts) | NIST 800-53 AC-2(12), SOC 2 CC6.1, HIPAA 164.312(d) |
| T1078.004 (Cloud Accounts) | NIST 800-53 AC-2(12), CSA CCM IAM-02 |
| T1059 (Command and Scripting) | NIST 800-53 CM-7(4), CIS Control 2.7 |
| T1059.001 (PowerShell) | NIST 800-53 CM-7(4), CIS Control 2.7 |
| T1021 (Remote Services) | NIST 800-53 AC-17, CIS Control 12.1 |
| T1486 (Data Encrypted for Impact) | NIST 800-53 CP-9, CIS Control 11.2 |
| T1566 (Phishing) | NIST 800-53 AT-2, CIS Control 14.1 |

---

## Inference Rules

### Confidence Scoring

Inferences are assigned confidence scores (0.0-1.0):

| Score Range | Meaning | When to Use |
|-------------|---------|-------------|
| 0.9-1.0 | High confidence | Direct mapping exists (tactic → problem) |
| 0.7-0.9 | Medium-high | Strong correlation (technique → compliance) |
| 0.5-0.7 | Medium | Reasonable inference (query pattern → limitation) |
| 0.3-0.5 | Low-medium | Educated guess |
| 0.0-0.3 | Low | Placeholder needed |

### Inference Sources

| Field | Primary Source | Fallback Source | Confidence |
|-------|----------------|-----------------|------------|
| Problem Statement | Tactic mapping | Technique description | 0.8 |
| Kill Chain Phase | Tactic mapping | - | 0.9 |
| Compliance Frameworks | Technique mapping | Tactic category | 0.7 |
| Limitations | Query analysis | Default list | 0.6 |
| Assumptions | Data source requirements | Default list | 0.7 |

---

## ISO 8601 Duration Parsing

### Format Reference

| Format | Meaning | Example |
|--------|---------|---------|
| PT{n}S | n seconds | PT30S = 30 seconds |
| PT{n}M | n minutes | PT5M = 5 minutes |
| PT{n}H | n hours | PT1H = 1 hour |
| P{n}D | n days | P1D = 1 day |
| P{n}W | n weeks | P1W = 1 week |
| P{n}M | n months | P1M = 1 month |
| P{n}Y | n years | P1Y = 1 year |

### Combined Formats

| Format | Meaning |
|--------|---------|
| PT1H30M | 1 hour 30 minutes |
| P1DT12H | 1 day 12 hours |
| P14D | 14 days |
| PT5M | 5 minutes |

### Parsing Code

```python
import re

def parse_iso_duration(duration):
    """Parse ISO 8601 duration to human-readable string."""
    if not duration:
        return "Not specified"

    # Time components (PT prefix)
    time_pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    # Date components (P prefix without T)
    date_pattern = r'P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)W)?(?:(\d+)D)?'

    parts = []

    # Parse time components
    time_match = re.search(time_pattern, duration)
    if time_match:
        hours, minutes, seconds = time_match.groups()
        if hours:
            parts.append(f"{hours} hour{'s' if int(hours) != 1 else ''}")
        if minutes:
            parts.append(f"{minutes} minute{'s' if int(minutes) != 1 else ''}")
        if seconds:
            parts.append(f"{seconds} second{'s' if int(seconds) != 1 else ''}")

    # Parse date components
    date_match = re.search(date_pattern, duration)
    if date_match:
        years, months, weeks, days = date_match.groups()
        if years:
            parts.append(f"{years} year{'s' if int(years) != 1 else ''}")
        if months:
            parts.append(f"{months} month{'s' if int(months) != 1 else ''}")
        if weeks:
            parts.append(f"{weeks} week{'s' if int(weeks) != 1 else ''}")
        if days:
            parts.append(f"{days} day{'s' if int(days) != 1 else ''}")

    return " ".join(parts) if parts else duration

# Examples
parse_iso_duration("PT30M")   # "30 minutes"
parse_iso_duration("P14D")    # "14 days"
parse_iso_duration("PT1H30M") # "1 hour 30 minutes"
parse_iso_duration("P1DT12H") # "1 day 12 hours"
```

---

## Entity Mapping Reference

### Supported Entity Types

| Entity Type | Common Identifiers | Description |
|-------------|-------------------|-------------|
| Account | Name, AadUserId, Sid, ObjectGuid, NTDomain, DnsDomain | User accounts |
| Host | HostName, DnsDomain, NTDomain, AzureID, OMSAgentID | Computer systems |
| IP | Address | IP addresses |
| URL | Url | Web addresses |
| File | Name, Directory | Files |
| FileHash | Algorithm, Value | File hashes |
| Process | ProcessId, CommandLine | Running processes |
| RegistryKey | Hive, Key | Windows registry |
| RegistryValue | Name, Value | Registry values |
| MailMessage | Recipient, Sender, Subject | Email messages |
| Mailbox | MailboxPrimaryAddress, DisplayName | Email mailboxes |
| MailCluster | ClusterSourceType, ClusterSourceIdentifier | Email clusters |
| CloudApplication | AppId, Name | Cloud applications |
| AzureResource | ResourceId | Azure resources |
| DNS | DomainName | DNS records |
| SecurityGroup | ObjectGuid, DistinguishedName | Security groups |

### Entity Mapping Structure

```json
{
  "entityMappings": [
    {
      "entityType": "Host",
      "fieldMappings": [
        {
          "identifier": "HostName",
          "columnName": "DeviceName"
        }
      ]
    },
    {
      "entityType": "Account",
      "fieldMappings": [
        {
          "identifier": "Name",
          "columnName": "AccountName"
        },
        {
          "identifier": "NTDomain",
          "columnName": "AccountDomain"
        }
      ]
    },
    {
      "entityType": "Process",
      "fieldMappings": [
        {
          "identifier": "ProcessId",
          "columnName": "ProcessId"
        },
        {
          "identifier": "CommandLine",
          "columnName": "ProcessCommandLine"
        }
      ]
    }
  ]
}
```

