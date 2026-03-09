# SOC Use Case Form Filling Guide

Guide for completing SOC use case documentation from Sentinel ARM templates.

## Determine Your Workflow

Check what input you have:

| Input Type | Workflow |
|------------|----------|
| ARM Template JSON | Automated Workflow |
| KQL Query Only | Manual Workflow |
| Existing Documentation | Enhancement Workflow |

---

## Automated Workflow (ARM Template)

For Sentinel analytics rules exported as ARM templates.

### Step 1: Extract Metadata

Parse `resources[0].properties` from the ARM template JSON to extract:

| Field | JSON Path | Output Section |
|-------|-----------|----------------|
| `display_name` | `.displayName` | Use Case Name |
| `description` | `.description` | Purpose |
| `severity` | `.severity` | SOC Notification |
| `tactics` | `.tactics[]` | MITRE Mapping |
| `techniques` | `.techniques[]` | MITRE Mapping |
| `entity_mappings` | `.entityMappings[]` | Alert Fields |
| `query` | `.query` | Detection Logic |

### Step 2: Infer Missing Sections

Use the inference mappings in this guide (see Form Structure sections) to infer:
- Problem Statement from tactic
- Kill Chain Phase from tactic
- Compliance Frameworks from technique
- Assumptions from data sources

### Step 3: Generate Documentation

Copy `TEMPLATE.md` and replace all `{PLACEHOLDER}` values with extracted/inferred content.

### Step 4: Fill Remaining Placeholders

Search for `[HUMAN INPUT REQUIRED]` and complete:

| Placeholder | How to Fill |
|-------------|-------------|
| Process Owner | Ask detection engineering team lead |
| Investigation Steps | Consult SOC analysts or existing runbooks |
| False Positive Sources | Review historical alert data |

---

## Manual Workflow (KQL Query Only)

### Step 1: Identify Tables

```kql
DeviceProcessEvents  // → MDE connector
| where ...
```

### Step 2: Extract Thresholds

```kql
| where count_ >= 5        // Threshold: 5
```

### Step 3: Fill Form Sections

Complete each section below manually.

---

## Form Structure

### Section 1: Use Case Metadata

| Field | Format | Source |
|-------|--------|--------|
| Use Case ID | `UC-SENTINEL-{CATEGORY}-{SEQ}` | Generate |
| Name | Title case | `properties.displayName` |
| Rule ID | GUID | Extract from `resources[0].id` |
| Severity | Informational/Low/Medium/High | `properties.severity` |

### Section 2: Purpose & Problem Statement

**Purpose:** Extract from `properties.description`
- Remove author attribution (move to References)
- Remove URLs (move to References)

**Problem Statement:** Infer from tactic:
| Tactic | Problem Statement |
|--------|-------------------|
| Persistence | Attackers establishing persistence mechanisms to maintain access |
| CredentialAccess | Credentials being harvested or stolen for unauthorized access |
| InitialAccess | Unauthorized entry attempts to gain initial foothold |
| LateralMovement | Attackers moving through the environment between systems |
| Exfiltration | Sensitive data being stolen from the environment |

### Section 3: Requirements Statement

Infer from technique:
| Technique | Compliance Frameworks |
|-----------|----------------------|
| T1543 | NIST 800-53 CM-7, CIS Control 2.5 |
| T1110 | NIST 800-53 AC-7, PCI-DSS 8.1.6 |
| T1078 | NIST 800-53 AC-2(12), SOC 2 CC6.1 |

### Section 4: SMART Objectives

Each objective must satisfy:
- **S**pecific: What exactly will be detected?
- **M**easurable: How to measure success?
- **A**ssignable: Who is responsible?
- **R**ealistic: Is it achievable with current data?
- **T**ime-related: Detection timeframe?

### Section 5: SOC Notification

**Severity Response Matrix:**
| Severity | Priority | Response SLA |
|----------|----------|--------------|
| Informational | P4 | 24 hours |
| Low | P3 | 8 hours |
| Medium | P2 | 4 hours |
| High | P1 | 1 hour |

### Section 6: Component Names

List Sentinel components:
- Analytics Rule name
- Data Connectors used
- Related Workbooks
- Automation Playbooks
- Watchlists referenced

### Section 7: Data Sources

| Table | Connector | Ingestion |
|-------|-----------|-----------|
| DeviceProcessEvents | Microsoft Defender for Endpoint | M365 Defender |
| SigninLogs | Azure Active Directory | Diagnostic Settings |
| SecurityEvent | Windows Security Events | MMA/AMA Agent |

### Section 8: Detection Logic

**Include:**
- KQL query (full text)
- Query frequency (`properties.queryFrequency`)
- Lookback period (`properties.queryPeriod`)
- Trigger threshold (`properties.triggerThreshold`)

**Parse ISO durations:**
| Format | Readable |
|--------|----------|
| PT5M | 5 minutes |
| PT30M | 30 minutes |
| PT1H | 1 hour |
| P1D | 1 day |
| P14D | 14 days |

### Section 9: Entity Mappings

Extract from `properties.entityMappings[]`:
| Entity Type | Identifier | Column |
|-------------|------------|--------|
| Host | HostName | DeviceName |
| Account | Name | AccountName |
| Process | ProcessId | ProcessId |

### Section 10: MITRE ATT&CK Mapping

Extract from:
- `properties.tactics[]`
- `properties.techniques[]`
- `properties.subTechniques[]`

### Section 11: Cyber Kill Chain

Map from tactic:
| Tactic | Kill Chain Phase |
|--------|------------------|
| Persistence | Installation |
| CredentialAccess | Exploitation |
| InitialAccess | Delivery/Exploitation |
| LateralMovement | Actions on Objectives |

### Section 12: SOC Response

**Investigation Steps:** Check KQL for `// INVESTIGATION STEPS:` comments

**False Positive Guidance:** Check KQL for `// FALSE POSITIVE:` comments

If not in KQL, mark `[HUMAN INPUT REQUIRED]`

### Section 13: Assumptions & Limitations

**Assumptions (infer from data sources):**
- Required connectors are configured
- Tables are populated with complete data
- Baseline data exists (if applicable)

**Limitations (infer from query):**
- Query frequency introduces detection delay
- Threshold may miss low-volume attacks

### Section 14: Alternative Solutions

`[HUMAN INPUT REQUIRED]` - Document other approaches considered

### Section 15: Deliverable Profile

| Field | Source |
|-------|--------|
| File Name | Generate from use case ID |
| Process Owner | `[HUMAN INPUT REQUIRED]` |
| Original Author | Extract from description |
| Policy/Procedure | `[HUMAN INPUT REQUIRED]` |
| Industry Reference | Infer from techniques |
| Effective Date | Current date |

---

## Validation Checklist

Before finalizing:

- [ ] All `[HUMAN INPUT REQUIRED]` placeholders resolved
- [ ] MITRE techniques are valid (check attack.mitre.org)
- [ ] Data sources match actual Sentinel connectors
- [ ] Query frequency aligns with detection requirements
- [ ] Investigation steps are actionable
- [ ] Process owner has acknowledged ownership
- [ ] Version history started
