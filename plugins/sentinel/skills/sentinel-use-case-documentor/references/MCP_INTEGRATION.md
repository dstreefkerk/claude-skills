# MCP Server Integration Guide

Optional MCP servers that enhance documentation quality when available. These servers provide real-time access to threat intelligence, detection content, and Sentinel workspace data.

---

## mitreattack

**Purpose:** Look up official MITRE ATT&CK definitions, tactic/technique descriptions, groups, software, and mitigations.

### Available Tools

| Tool | Purpose |
|------|---------|
| `get_technique_by_id` | Get detailed technique info by ID (e.g., T1055) |
| `get_techniques` | List techniques with pagination support |
| `get_techniques_by_tactic` | Get all techniques for a specific tactic |
| `get_tactics` | List all MITRE ATT&CK tactics |
| `get_groups` | List threat actor groups |
| `get_techniques_used_by_group` | Get techniques used by a specific group |
| `get_software` | List malware and tools |
| `get_mitigations` | List mitigations |
| `get_techniques_mitigated_by_mitigation` | Get techniques addressed by a mitigation |

### Key Parameters

```python
# get_technique_by_id
technique_id: str  # Required. Format: "T1055" or "T1055.001"
domain: str        # Optional. Default: "enterprise-attack"

# get_techniques_by_tactic
tactic_shortname: str  # Required. Use lowercase with hyphens
domain: str            # Optional. Default: "enterprise-attack"
```

### Tactic Shortnames (use these exact values)

| Shortname | Full Name |
|-----------|-----------|
| `reconnaissance` | Reconnaissance |
| `resource-development` | Resource Development |
| `initial-access` | Initial Access |
| `execution` | Execution |
| `persistence` | Persistence |
| `privilege-escalation` | Privilege Escalation |
| `defense-evasion` | Defense Evasion |
| `credential-access` | Credential Access |
| `discovery` | Discovery |
| `lateral-movement` | Lateral Movement |
| `collection` | Collection |
| `command-and-control` | Command and Control |
| `exfiltration` | Exfiltration |
| `impact` | Impact |

### Documentation Enhancement Examples

**Before (basic):**
```
T1543.003 - Windows Service
```

**After (enriched with MITRE data):**
```
T1543.003 - Create or Modify System Process: Windows Service

Adversaries may create or modify Windows services to repeatedly execute
malicious payloads as part of persistence. When Windows boots up, it starts
programs or applications called services that perform background system
functions.

Related Mitigations: M1040 (Behavior Prevention on Endpoint), M1028 (Operating
System Configuration), M1047 (Audit)
```

---

## MS-Sentinel-MCP-Server

**Purpose:** Query Sentinel workspace for table schemas, validate KQL syntax, retrieve analytics rules, and access workspace configuration.

### Available Tools

| Tool | Purpose |
|------|---------|
| `sentinel_query_validate` | Validate KQL syntax locally (no execution) |
| `sentinel_logs_table_schema_get` | Get column names and types for a table |
| `sentinel_logs_tables_list` | List available tables in workspace |
| `sentinel_logs_search` | Execute KQL queries against workspace |
| `sentinel_logs_search_with_dummy_data` | Test KQL with mock data |
| `sentinel_analytics_rule_get` | Get full details of an analytics rule |
| `sentinel_analytics_rule_list` | List all analytics rules |
| `sentinel_connectors_list` | List configured data connectors |
| `sentinel_workspace_get` | Get workspace metadata |

### Key Tool Usage

#### Validate KQL Syntax
```python
sentinel_query_validate(kwargs={"query": "SecurityEvent | where EventID == 4625"})
```
**Response:**
```json
{
  "valid": true,
  "errors": [],
  "result": "Query validation passed. The KQL syntax appears to be correct."
}
```

#### Get Table Schema
```python
sentinel_logs_table_schema_get(kwargs={"table": "DeviceProcessEvents"})
```
**Response:**
```json
{
  "table": "DeviceProcessEvents",
  "schema": [
    {"name": "TimeGenerated", "type": "datetime"},
    {"name": "DeviceName", "type": "string"},
    {"name": "ProcessCommandLine", "type": "string"},
    {"name": "AccountName", "type": "string"}
  ]
}
```

#### Get Analytics Rule Details
```python
sentinel_analytics_rule_get(kwargs={"id": "rule-guid-or-name"})
```
**Response includes:**
- `query`: The KQL detection logic
- `severity`: Rule severity
- `tactics`: MITRE tactics array
- `techniques`: MITRE techniques array
- `description`: Rule description
- `enabled`: Whether rule is active

### Documentation Enhancement Use Cases

1. **Validate Data Source Requirements**
   - Use `sentinel_logs_tables_list` to confirm required tables exist
   - Use `sentinel_logs_table_schema_get` to verify expected columns

2. **Validate Entity Mappings**
   - Get table schema to confirm entity mapping fields exist
   - Verify column types match expected entity types

3. **Test Detection Logic**
   - Use `sentinel_query_validate` to check KQL syntax
   - Use `sentinel_logs_search_with_dummy_data` for logic testing

4. **Enrich Data Source Documentation**
   - Use `sentinel_connectors_list` to identify required connectors
   - Document connector dependencies in use case

---

## detection-nexus

**Purpose:** Search for related detection rules across multiple platforms (Splunk, Elastic, Sigma, CrowdStrike, etc.) for cross-referencing and comparison.

### Available Tools

| Tool | Purpose |
|------|---------|
| `search_rules` | General search with multiple filters |
| `get_rule` | Get complete rule details by ID |
| `get_rule_markdown` | Get rule formatted as markdown |
| `search_by_mitre` | Search by technique IDs or tactics |
| `search_by_query_text` | Search within detection query content |
| `list_providers` | List available detection providers |
| `get_stats` | Get database statistics |

### Key Parameters

#### search_rules
```python
search_rules(
    query="powershell",           # Text search in title/description
    providers="splunk,elastic",   # Comma-separated providers
    severities="high,critical",   # Comma-separated severities
    mitre_techniques="T1059.001", # Comma-separated technique IDs
    mitre_tactics="execution",    # Comma-separated tactic shortnames
    limit=20,                     # Max results (default: 20)
    offset=0                      # Pagination offset
)
```

#### search_by_mitre
```python
search_by_mitre(
    technique_ids="T1055,T1055.001",     # Comma-separated
    tactic_names="persistence,defense-evasion",  # Comma-separated
    include_sub_techniques=True,         # Include sub-techniques
    limit=20
)
```

### Valid Parameter Values

**Providers:** `splunk`, `elastic`, `sigma`, `crowdstrike`, `microsoft`, `chronicle`, `qradar`, `sentinel`

**Severities:** `critical`, `high`, `medium`, `low`, `informational`

**MITRE Techniques:** Use format `T1055`, `T1055.001` (uppercase T, include sub-techniques)

**MITRE Tactics:** Use lowercase with hyphens: `defense-evasion`, `command-and-control`

### Documentation Enhancement Examples

**Find Related Detections:**
```python
# For a rule detecting T1059.001 (PowerShell)
search_by_mitre(technique_ids="T1059.001", limit=10)
```

**Cross-Platform Comparison:**
```python
# Find similar detections in other platforms
search_rules(query="suspicious powershell", providers="splunk,elastic,sigma")
```

**Get Rule Details for Reference:**
```python
# Get full rule for documentation
get_rule(rule_id="splunk-powershell-123")

# Or as formatted markdown
get_rule_markdown(rule_id="splunk-powershell-123")
```

### Adding Related Detections Section

Use detection-nexus to populate a "Related Detections" section:

```markdown
## Related Community Detections

| Platform | Rule | Severity |
|----------|------|----------|
| Sigma | Suspicious PowerShell Execution | High |
| Elastic | PowerShell Script with Encoded Commands | High |
| Splunk | Malicious PowerShell Process Patterns | Critical |
```

---

## Integration Workflow

### Enhanced Documentation Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Parse ARM Template                            │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  MS-Sentinel-MCP-Server                                  │    │
│  │  • sentinel_query_validate() - Validate KQL syntax       │    │
│  │  • sentinel_logs_table_schema_get() - Verify columns     │    │
│  │  • sentinel_connectors_list() - Document requirements    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  mitreattack                                             │    │
│  │  • get_technique_by_id() - Get official descriptions     │    │
│  │  • get_mitigations() - Document defensive controls       │    │
│  │  • get_techniques_used_by_group() - Threat actor context │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  detection-nexus                                         │    │
│  │  • search_by_mitre() - Find related detections           │    │
│  │  • get_rule_markdown() - Format for documentation        │    │
│  │  • search_rules() - Cross-platform comparison            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         │                                        │
│                         ▼                                        │
│                  Generate Documentation                          │
└─────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Integration

| Step | Action | MCP Server | Tool |
|------|--------|------------|------|
| 1 | Validate KQL syntax | MS-Sentinel | `sentinel_query_validate` |
| 2 | Verify table/column existence | MS-Sentinel | `sentinel_logs_table_schema_get` |
| 3 | Document data connector requirements | MS-Sentinel | `sentinel_connectors_list` |
| 4 | Enrich MITRE technique descriptions | mitreattack | `get_technique_by_id` |
| 5 | Add mitigation recommendations | mitreattack | `get_techniques_mitigated_by_mitigation` |
| 6 | Find related community detections | detection-nexus | `search_by_mitre` |
| 7 | Add cross-platform references | detection-nexus | `get_rule_markdown` |

### Fallback Behavior

If MCP servers are not available:
- **KQL Validation:** Skip or use basic syntax checking
- **MITRE Enrichment:** Use built-in mappings from REFERENCE.md
- **Related Detections:** Omit section or note "MCP server unavailable"
- **Table Schema:** Document based on ARM template metadata only

### Error Handling

```python
# Check for errors in responses
if "error" in response:
    # Fall back to built-in data
    use_reference_md_mappings()
else:
    # Use MCP-enriched data
    use_mcp_response(response)
```

---

## Quick Reference

### Common Integration Patterns

**Pattern 1: Validate and Document Data Sources**
```
1. sentinel_logs_tables_list()           → Get available tables
2. sentinel_logs_table_schema_get()      → Verify columns exist
3. sentinel_connectors_list()            → Identify required connectors
```

**Pattern 2: Enrich MITRE Mapping**
```
1. Parse technique IDs from ARM template
2. get_technique_by_id() for each        → Get full descriptions
3. get_mitigations() if relevant         → Add defensive context
```

**Pattern 3: Add Related Detections**
```
1. Extract technique IDs from rule
2. search_by_mitre(technique_ids=...)    → Find similar rules
3. get_rule_markdown() for top results   → Format for documentation
```

**Pattern 4: Full Enrichment Pipeline**
```
1. sentinel_query_validate()             → Validate KQL
2. sentinel_logs_table_schema_get()      → Verify schema
3. get_technique_by_id()                 → MITRE enrichment
4. search_by_mitre()                     → Related detections
5. Generate comprehensive documentation
```
