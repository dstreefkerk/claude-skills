---
name: sentinel-use-case-documentor
description: Documents Microsoft Sentinel analytics rules as comprehensive SOC use cases. Use when the user wants to document a Sentinel rule, create SOC documentation, generate use case docs from an ARM template, or document a KQL detection query.
metadata:
  version: "1.0"
---

# Sentinel Use Case Documentor

Transforms Sentinel ARM template exports into standardized SOC use case documentation.

## When to Use

- User provides a Sentinel ARM template JSON file
- User asks to "document" a detection rule or analytics rule
- User wants SOC/SIEM use case documentation

**Example:** `Document this Sentinel rule: @rule.json`

## Two Modes

| Mode | Use When | Behavior |
|------|----------|----------|
| **Quick** | Batch processing, time-sensitive | Generate with `[HUMAN INPUT REQUIRED]` placeholders |
| **Guided** | Critical rules, compliance audits | Interactive Q&A before generating |

---

## Workflow

### Step 0: Load References

Read these files to understand expected output:
1. `expected_output.md` - Complete example
2. `references/TEMPLATE.md` - Copyable template

### Step 1: Ask Mode

Use AskUserQuestion: "How would you like to document this rule?"
- Quick Mode - Generate with placeholders
- Guided Mode - Interactive Q&A

### Step 2: Parse ARM Template

Extract from `resources[0].properties`:

| Field | Path | Output Section |
|-------|------|----------------|
| displayName | `.displayName` | Use Case Name |
| description | `.description` | Purpose |
| severity | `.severity` | SOC Notification |
| query | `.query` | Detection Logic |
| queryFrequency | `.queryFrequency` | Timing |
| queryPeriod | `.queryPeriod` | Timing |
| tactics | `.tactics[]` | MITRE Mapping |
| techniques | `.techniques[]` | MITRE Mapping |
| entityMappings | `.entityMappings[]` | Alert Fields |

### Step 3: Analyze KQL Query

Identify from query field:
- **Tables**: Map to connectors (see `references/REFERENCE.md` for full mapping)
- **Thresholds**: `count() >= N`, `where X > N`
- **Time windows**: `bin(TimeGenerated, Xm)`, `ago(Xd)`
- **Embedded docs**: `// DESCRIPTION:`, `// INVESTIGATION STEPS:`, `// FALSE POSITIVE:`

### Step 4: Infer Missing Sections

Apply inference rules from `references/REFERENCE.md`:
- Problem Statement <- tactic
- Kill Chain Phase <- tactic
- Compliance Frameworks <- technique

### Step 5: Generate Documentation

Copy `references/TEMPLATE.md` and fill placeholders.

**Quick Mode**: Fill what you can, mark gaps with `[HUMAN INPUT REQUIRED]`

**Guided Mode**: Ask for each gap:
- "What security problem does this detection address?"
- "Who owns this detection?"
- "How should SOC be notified?"
- "What investigation steps should analysts follow?"

### Step 6: Write Output

Save to `{original_filename}_UseCase.md` in the same directory.

---

## Reference Files

| File | Purpose |
|------|---------|
| `references/TEMPLATE.md` | Copyable template with placeholders |
| `references/FORMS.md` | Guide explaining each section |
| `references/REFERENCE.md` | Technical details: ARM parsing, KQL analysis, inference mappings |
| `references/MCP_INTEGRATION.md` | Optional MCP server enhancements |
| `expected_output.md` | Complete example output |
| `sample_input.json` | Example ARM template |

---

## MCP Enhancement (Optional)

If available, use these MCP servers to enrich documentation:
- `mitreattack` - Official MITRE technique descriptions
- `MS-Sentinel-MCP-Server` - Validate table schemas and KQL
- `detection-nexus` - Find related detections

See `references/MCP_INTEGRATION.md` for details.
