---
name: sentinel-arm-generator
description: Automatically generates deployment-ready Microsoft Sentinel Analytic Rule ARM templates from KQL queries with intelligent MITRE mappings, entity extraction, and metadata generation
metadata:
  version: "1.0"
---

# Microsoft Sentinel ARM Template Generator

Transform tested KQL detection queries into complete, deployment-ready Microsoft Sentinel Analytic Rule ARM templates. Eliminates manual overhead by intelligently inferring rule names, MITRE ATT&CK mappings, entity mappings, and metadata from your KQL query and conversation context.

> **CRITICAL**: Before generating any ARM template, you MUST read the files in the `references/` folder. They contain required technical specifications for entity mappings, MITRE patterns, ARM schema, and validation rules.

## Capabilities

- **Intelligent Rule Naming**: Auto-generates displayName based on detection purpose
- **MITRE ATT&CK Mapping**: Suggests tactics, techniques, and sub-techniques based on threat patterns
- **Entity Extraction**: Analyzes KQL to map entities (Account, IP, Host, Process, File, URL, etc.)
- **Severity Assignment**: Infers severity level based on threat type
- **Query Frequency Optimization**: Recommends queryFrequency and queryPeriod
- **ARM Template Compliance**: Generates valid templates for API version 2023-12-01-preview
- **GUID Generation**: Creates unique rule identifiers
- **Context-Aware**: Leverages conversation context to understand detection purpose

## Input Requirements

### Primary Input
- **KQL Query**: The tested detection query ready for deployment
- **Conversation Context**: Detection purpose from current session

### Automatically Inferred
- Rule display name and description
- MITRE ATT&CK tactics/techniques/sub-techniques
- Entity mappings from KQL output columns
- Severity level (High/Medium/Low/Informational)
- Query frequency and lookback period
- Trigger operator and threshold

### Optional User Overrides
- Custom rule name
- Specific MITRE mappings
- Preferred severity level
- Custom query frequency/period
- Specific entity mappings

## How to Use

### Basic Usage (Maximum Automation)

```
@sentinel-arm-generator

I've been working on this KQL query for detecting suspicious Azure AD sign-ins:

SigninLogs
| where ResultType != "0"
| where AppDisplayName != "Microsoft Authentication Broker"
| summarize FailedAttempts = count() by UserPrincipalName, IPAddress, bin(TimeGenerated, 5m)
| where FailedAttempts >= 5
| project TimeGenerated, UserPrincipalName, IPAddress, FailedAttempts

Generate the ARM template for deployment.
```

**Skill will automatically**:
- Generate name: "Multiple Failed Azure AD Sign-In Attempts from Single IP"
- Assign severity: High
- Map MITRE tactics: [InitialAccess, CredentialAccess]
- Map techniques: [T1078, T1110]
- Extract entities: Account (UserPrincipalName), IP (IPAddress)
- Set frequency: PT5M / PT10M (5 min checks, 10 min lookback with buffer)
- Generate deployment-ready ARM template

### With Custom Overrides

```
@sentinel-arm-generator

Generate ARM template for this KQL detecting file creation in temp directories:

DeviceFileEvents
| where FolderPath contains "\\Temp\\"
| where FileOriginReferrerUrl startswith "http"
| project TimeGenerated, DeviceName, FileName, FolderPath, FileOriginUrl

Use severity: Medium
Add custom description: Detects potentially suspicious file downloads to temp folders
```

### Batch Generation

```
@sentinel-arm-generator

Generate ARM templates for all three KQL queries we discussed:
1. The brute force detection query
2. The privilege escalation detection query
3. The data exfiltration detection query
```

## Output

### ARM Template
- Generates standard Azure Resource Manager deployment template
- Ready for deployment via Azure CLI, PowerShell, or Portal
- Includes workspace parameter for flexible deployment

### File Output
- JSON file: `sentinel-rule-{rule-name}.json`
- Deployment instructions: Azure CLI/Portal commands
- Validation summary: Lists auto-generated fields and rationale

## Scripts

Located in `scripts/` folder:

- `scripts/generate_arm_template.py`: Main template generation engine
- `scripts/mitre_attack_mapper.py`: MITRE ATT&CK framework mapping
- `scripts/entity_extractor.py`: KQL query parser for entity identification
- `scripts/kql_analyzer.py`: Query analysis for severity/frequency recommendations

## Key Concepts

### Entity Mapping

Automatically identifies and maps Sentinel entity types from KQL output columns:
- **Account**: UserPrincipalName, AccountName, TargetUserName
- **IP**: IPAddress, SourceIP, DestinationIP, ClientIP
- **Host**: DeviceName, ComputerName, HostName
- **Process**: ProcessName, ProcessCommandLine
- **File**: FileName, FilePath, FolderPath
- **URL**: Url, FileOriginUrl, RemoteUrl

**Constraint**: Maximum 5 entity mappings, each type used only once.

**Required**: Consult [references/ENTITY_MAPPINGS.md](references/ENTITY_MAPPINGS.md) for complete column patterns and identifiers.

### MITRE ATT&CK Mapping

Auto-maps tactics and techniques based on detection patterns:
- Failed logins -> InitialAccess (T1078), CredentialAccess (T1110)
- Service creation -> Persistence (T1543)
- Remote PowerShell -> LateralMovement (T1021.006)
- Large data transfers -> Exfiltration (T1041)

**Required**: Consult [references/MITRE_MAPPINGS.md](references/MITRE_MAPPINGS.md) for complete tactic/technique mappings.

### Severity Assignment

| Level | Triggers |
|-------|----------|
| High | Credential compromise, privilege escalation, lateral movement, exfiltration, malware |
| Medium | Policy violations, suspicious behavior, config changes, failed security events |
| Low | Compliance monitoring, audit events, baseline deviations |
| Informational | Usage statistics, inventory changes, routine events |

### Query Frequency

**Critical**: Always set `queryPeriod` > `queryFrequency` to handle ingestion lag.

| Detection Type | Frequency | Period |
|---------------|-----------|--------|
| Real-Time Critical | PT5M | PT10M |
| Real-Time Standard | PT5M | PT15M |
| Hourly | PT1H | PT2H |
| Daily | P1D | P1D (with TimeGenerated filter) |

### Custom Details

Surface KQL columns into incidents without alertDescriptionFormat limits:

```json
"customDetails": {
  "RiskLevel": "RiskLevel",
  "ProcessName": "ProcessName",
  "TargetResource": "TargetResource"
}
```

### Event Grouping

| Aggregation | Use When |
|-------------|----------|
| SingleAlert | Threshold-based detections, correlation rules |
| AlertPerResult | Each row is distinct incident |

## Azure Validation Rules

Critical constraints enforced by Azure:

| Constraint | Limit | Impact |
|------------|-------|--------|
| alertDescriptionFormat parameters | Max 3 | Deployment fails |
| entityMappings | Max 5 | Deployment fails |
| Entity type | Once per type | Deployment fails |
| templateVersion (custom rules) | Must NOT include | Deployment fails |

## Limitations

### Technical
- Complex queries with dynamic schemas may need manual entity review
- Entity extraction works best with standard Sentinel tables
- Multi-table joins may need manual entity validation

### Not Supported
- **Fusion/ML rules**: Different rule type
- **NRT rules**: Different ARM schema (no frequency/period properties)
- **Multi-rule correlation**: Requires custom implementation

**Required**: Consult [references/BEST_PRACTICES.md](references/BEST_PRACTICES.md) for validation rules and Sentinel table reference.

## Deployment

### Azure CLI
```bash
az deployment group create \
  --resource-group <rg-name> \
  --template-file sentinel-rule-{rule-name}.json \
  --parameters workspace=<workspace-name>
```

### Azure PowerShell
```powershell
New-AzResourceGroupDeployment `
  -ResourceGroupName <rg-name> `
  -TemplateFile sentinel-rule-{rule-name}.json `
  -workspace <workspace-name>
```

### Azure Portal
1. Navigate to Deploy a custom template
2. Upload generated JSON file
3. Provide workspace parameter
4. Review and deploy

## Required Reference Files

**IMPORTANT**: You MUST read and apply the reference files when generating ARM templates. These contain critical technical specifications that are NOT duplicated in this file.

| File | Purpose | When to Use |
|------|---------|-------------|
| [references/ARM_TEMPLATE.md](references/ARM_TEMPLATE.md) | Template structure, schema, JSON escaping | **Every generation** - contains ARM schema requirements |
| [references/ENTITY_MAPPINGS.md](references/ENTITY_MAPPINGS.md) | Entity types, identifiers, column patterns | **Every generation** - required for entity extraction |
| [references/MITRE_MAPPINGS.md](references/MITRE_MAPPINGS.md) | Tactics, techniques, detection patterns | **Every generation** - required for MITRE mapping |
| [references/BEST_PRACTICES.md](references/BEST_PRACTICES.md) | Quality checks, limitations, Sentinel tables | **Every generation** - required for validation |

**Failure to consult these references will result in incorrect or invalid ARM templates.**

## API Version

Microsoft.SecurityInsights: **2023-12-01-preview**
