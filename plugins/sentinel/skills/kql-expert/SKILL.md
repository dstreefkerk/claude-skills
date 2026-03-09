---
name: kql-expert
description: MUST BE USED PROACTIVELY when user reads/checks/reviews/analyzes any .kql file, writes KQL queries, or works with Microsoft Sentinel/M365 Defender detection rules. Invoke IMMEDIATELY when .kql file extension detected. Expert in query optimization, schema validation, and best practice compliance.
---

# KQL Expert - Microsoft Sentinel & Azure Monitor Query Specialist

Expert guidance for Kusto Query Language (KQL) covering query optimization, schema validation against M365/Sentinel tables, analytics rule development, ASIM normalization, threat hunting, and SPL migration.

## Capabilities

- **Schema Validation**: Validate queries against M365 Defender and Sentinel table schemas via `schema_validator.py`
- **Query Optimization**: Analyze and optimize queries following filter-early principles and term indexing
- **Analytics Rules**: Develop scheduled/NRT rules with entity mapping, MITRE ATT&CK tags, watchlist integration
- **ASIM Normalization**: Source-agnostic detection using unifying parsers with filtering parameters
- **SPL Migration**: Convert Splunk queries to KQL with proper command mapping
- **Threat Hunting**: Create hypothesis-driven hunting queries with anomaly detection
- **False Positive Tuning**: Reduce alert fatigue via watchlists and automation rules
- **Cost Optimization**: Table plan selection, DCR transformations, commitment tiers

## Proactive Usage

**INVOKE THIS SKILL IMMEDIATELY when any of these conditions are met:**

### Primary Triggers (Invoke First)
| Condition | User Phrasing Examples |
|-----------|------------------------|
| **`.kql` file extension** | "Check @file.kql", "Review this .kql", "Look at @Detection.kql" |
| **KQL operators in content** | File contains `| where`, `| extend`, `| summarize`, `| join` |
| **Sentinel/M365 Defender context** | "analytics rule", "detection rule", "hunting query" |

### Secondary Triggers
| Trigger | Examples |
|---------|----------|
| **KQL query writing** | "Write a KQL query", "Create a detection for..." |
| **Performance issues** | "Query is slow", "timing out", "optimize this query" |
| **Syntax problems** | KQL validation fails, syntax errors |
| **Best practice review** | "Review for best practices", "Is this optimized?" |
| **SPL migration** | "Convert this Splunk query to KQL" |

### File Patterns
- `*.kql` - **Always invoke for this extension**
- Analytics rule ARM templates containing KQL
- Sentinel workbook queries
- Any file with KQL pipe operators (`| where`, `| extend`, etc.)

## Extended Thinking Framework

For complex KQL optimization challenges, apply systematic extended thinking:

### When to Use Extended Thinking
- **Complex Multi-Filter Optimization**: Queries with 5+ where clauses requiring selectivity analysis
- **Performance Regression Analysis**: Understanding why optimized queries sometimes perform worse
- **Cross-Table Join Optimization**: Complex scenarios involving multiple data sources
- **Detection Logic Preservation**: Ensuring optimizations don't break detection effectiveness

### Thinking Process
1. **Problem Understanding**: Current performance issue, constraints, available techniques
2. **Hypothesis Formation**: Filter selectivity predictions, string operation optimizations
3. **Testing Strategy**: Measure performance differences, validate optimization
4. **Solution Synthesis**: Best combination of optimizations, trade-offs
5. **Validation**: Verify performance targets met, detection effectiveness maintained

## Query Analysis Workflow

When reviewing or optimizing KQL:

1. **Read Best Practices**: Reference `references/kql_best_practices.md`
2. **Apply Extended Thinking**: For complex queries, reason through optimization approaches
3. **Validate Syntax**: Use schema validator for syntax checking
4. **Performance Baseline**: Test current query execution time
5. **Deep Analysis**: Consider multiple optimization approaches and trade-offs
6. **Identify Optimizations**: Apply string operator improvements
7. **Test Variants**: Create and test optimized versions
8. **Compare Results**: Document performance improvements
9. **Validate Assumptions**: Verify theoretical expectations match reality
10. **Recommend Implementation**: Provide final optimized query with rationale

## Scripts

Located in `scripts/` folder:

### schema_validator.py
Validates KQL queries against table schemas. **Always use this script instead of reading `environments.json` directly.**

Features:
- Table existence validation (M365, Sentinel, merged environments)
- Column type checking
- Magic function support (FileProfile, DeviceFromIP)
- Watchlist validation
- Similar name suggestions for typos

```python
from scripts.schema_validator import KQLSchemaValidator, format_schema_validation_result

validator = KQLSchemaValidator()  # Loads environments.json internally
result = validator.validate_query(query, environment='sentinel')
print(format_schema_validation_result(result))
```

**Do NOT read `environments.json` directly** - it's a large schema file meant for programmatic access only.

### kql_patterns.py
Reusable query templates for common scenarios:
- Analytics rule patterns (brute force, impossible travel, suspicious execution)
- Threat hunting patterns (IoC detection, lateral movement, anomaly detection, persistence)
- ASIM templates with filtering parameters
- Join optimization patterns

### kql_optimizer.py
Query analysis and performance optimization:
- Time filtering checks (missing, late placement)
- String operator analysis (contains vs has)
- Join optimization opportunities
- Aggregation anti-patterns
- ASIM parameter usage

### kql_validator.py
Query validation and compliance:
- Syntax validation
- Analytics rule constraints
- Entity mapping validation
- MITRE ATT&CK framework alignment
- Cross-workspace query limits

## References

Located in `references/` folder:

| File | Description | Access |
|------|-------------|--------|
| `environments.json` | M365 and Sentinel table schemas | **Scripts only** - use `schema_validator.py` |
| `ENVIRONMENTS.md` | Schema file documentation | Read directly |
| `kql_best_practices.md` | Detailed optimization guide | Read directly |
| `spl_to_kql_mapping.md` | SPL migration reference | Read directly |
| `asim_schemas.md` | ASIM parser reference | Read directly |

**Important**: Never read `environments.json` directly. It's a large data file (~500KB+) designed for programmatic access via `schema_validator.py`. Use the Python script to validate schemas.

## Key Optimization Principles

### 1. Filter Early (CRITICAL)

```kql
// BAD - Late filtering
SecurityEvent
| extend x = tolower(Account)
| join IdentityInfo on Account
| where TimeGenerated > ago(1h)  // Too late!

// GOOD - Time filter FIRST
SecurityEvent
| where TimeGenerated > ago(1h)
| where EventID == 4625
| join (IdentityInfo | where TimeGenerated > ago(1h)) on Account
```

### 2. Use Term Indexing

```kql
// BAD - Full scan
| where CommandLine contains "powershell"

// GOOD - Uses index (3+ chars)
| where CommandLine has "powershell"
```

### 3. ASIM with Filtering Parameters

```kql
// BAD - No filters
_Im_Authentication
| where TimeGenerated > ago(1h)

// GOOD - Filters pushed to sources
_Im_Authentication(starttime=ago(1h), endtime=now(), eventresult='Failure')
```

### 4. Watchlist Integration

```kql
// Use SearchKey for optimal joins
let allowlist = _GetWatchlist('TrustedIPs') | project SearchKey;
SigninLogs
| where TimeGenerated > ago(1d)
| where IPAddress !in (allowlist)
```

## Anti-Patterns to Avoid

| Pattern | Problem | Solution |
|---------|---------|----------|
| `contains` for terms | Full scan | Use `has` |
| `tolower(x) == "y"` | Row-by-row conversion | Use `x =~ "y"` |
| `search *` / `union *` | Scans all tables | Explicit table names |
| No TimeGenerated filter | Full history scan | Filter first |
| No time in subqueries | Subquery scans all | Add filter to each |
| `sort by \| take N` | Full sort | Use `top N by` |
| Large table on left | Inefficient join | Small table left |
| `parse` for structured strings | Fragile; breaks if schema changes | Use `extract()` or `parse_json()` |

### Contains Elimination Patterns

Expert patterns for replacing expensive `contains`:
- `contains ".Insert("` → `has "Insert"` ✅
- `contains "InstallProduct("` → `has "InstallProduct"` ✅
- `contains "function("` → `has "function"` ✅
- `contains "cmd /c"` → Keep contains (complex pattern) ❌

**Rule**: If the contains target has a 3+ character word boundary term, extract it for `has`.

### Robust String Parsing

The `parse` operator is sensitive to exact string formats and breaks silently when upstream schemas change (spacing, field order, new fields):

```kql
// FRAGILE - breaks if format changes
| parse KeyDescription with "KeyIdentifier=" KeyId ", KeyType=" KeyType ", KeyUsage=" KeyUsage

// ROBUST - extract with regex (tolerant of spacing/order changes)
| extend KeyId = extract(@"KeyIdentifier=([^,]+)", 1, KeyDescription)
| extend KeyType = extract(@"KeyType=([^,]+)", 1, KeyDescription)

// ROBUST - if the value is JSON-formatted
| extend ParsedKey = parse_json(newValue)
| extend KeyId = tostring(ParsedKey.KeyIdentifier)
```

**When to use each approach:**

| Method | Use When |
|--------|----------|
| `parse` | Format is guaranteed stable AND you need all fields in sequence |
| `extract()` | Need specific fields, format may vary, or fields may be reordered |
| `parse_json()` | Data is JSON (extract JSON portion first if prefixed with text) |

## Resource Thresholds

| Metric | Excessive | Throttled |
|--------|-----------|-----------|
| CPU Time | >100s | >1,000s |
| Time Span | >15 days | >90 days |
| Cross-Region | >3 | >6 |
| Query Timeout | 4 min default | 1 hour max |
| Result Limit | 500K records OR 64MB |

## Performance Targets

| Query Type | Target | Acceptable | Action if Exceeded |
|------------|--------|------------|-------------------|
| Detection Rules | < 5s | < 30s | Optimize filters, reduce time range |
| Dashboards | < 2s | < 5s | Pre-aggregate, reduce scope |
| Investigation Queries | < 60s | < 120s | Add time filters, sample data |
| Threat Hunting | < 120s | < 300s | Narrow scope, use summarization |

## Analytics Rule Constraints

- Query max: 10,000 characters
- Entity mappings: 10 max (3 identifiers each)
- Entities per alert: 500 max
- NRT rules: 50 per workspace, 30 alerts per execution
- Multi-workspace: 20 max
- Prohibited: `search *`, `union *`
- Required: Return `TimeGenerated` column

## Supported Environments

The skill validates against three environments (accessed via `schema_validator.py`):

| Environment | Tables | Use Case |
|-------------|--------|----------|
| `m365` | Defender XDR tables | Advanced Hunting |
| `sentinel` | Log Analytics tables | Microsoft Sentinel |
| `m365_with_sentinel` | Merged (auto-created) | Cross-platform queries |

## Table Schema Validation

```python
# Check available tables
validator = KQLSchemaValidator()
print(validator.get_available_environments())
# ['m365', 'sentinel', 'm365_with_sentinel']

# Get table schema
schema = validator.get_table_schema('sentinel', 'SecurityEvent')
print(schema.columns)  # {'TimeGenerated': 'datetime', 'EventID': 'int', ...}

# Validate query
result = validator.validate_query("""
SecurityEvent
| where TimeGenerated > ago(1h)
| where EventID == 4625
| project TimeGenerated, Account, IpAddress
""", environment='sentinel')

print(f"Valid: {result.is_valid}")
print(f"Tables: {result.referenced_tables}")
print(f"Unknown: {result.unknown_tables}")
```

## Join Strategy Reference

| Scenario | Hint | When |
|----------|------|------|
| Small right table (<100KB) | `hint.strategy=broadcast` | Dimension lookups |
| High-cardinality (>1M) | `hint.shufflekey=<key>` | IP, GUID joins |
| Small dimension table | Use `lookup` operator | Auto-broadcast |

```kql
// Broadcast for small tables
| join kind=inner hint.strategy=broadcast (SmallTable) on Key

// Shuffle for high-cardinality
| join kind=inner hint.shufflekey=IPAddress (LargeTable) on IPAddress
```

## ASIM Parser Quick Reference

| Schema | Parser | Key Parameters |
|--------|--------|----------------|
| Authentication | `_Im_Authentication` | starttime, endtime, eventresult, username_has_any |
| Network Session | `_Im_NetworkSession` | starttime, endtime, srcipaddr_has_any_prefix, dstportnumber |
| DNS | `_Im_Dns` | starttime, endtime, responsecodename, domain_has_any |
| Process Event | `_Im_ProcessEvent` | starttime, endtime, commandline_has_any, hostname_has_any |
| File Event | `_Im_FileEvent` | starttime, endtime, filename_has_any, filepath_has_any |
| Registry Event | `_Im_RegistryEvent` | starttime, endtime, registrykey_has_any |

See `references/asim_schemas.md` for complete schema documentation.

## SPL to KQL Quick Reference

| SPL | KQL | Notes |
|-----|-----|-------|
| `eval` | `extend` | `strcat()` for concat |
| `table` | `project` | Select columns |
| `stats count by x` | `summarize count() by x` | |
| `stats dc(x)` | `dcount(x)` | Distinct count |
| `stats values(x)` | `make_set(x)` | Unique values |
| `stats earliest(_time)` | `arg_min(TimeGenerated, *)` | |
| `stats latest(_time)` | `arg_max(TimeGenerated, *)` | |
| `if(a,b,c)` | `iff(a,b,c)` | Extra 'f' |
| `substr(x,1,5)` | `substring(x,0,5)` | 0-based! |
| `cidrmatch` | `ipv4_is_match()` | |

See `references/spl_to_kql_mapping.md` for complete mapping.

## Optimization Report Template

When reporting optimization results:

```
## Performance Analysis
| Version | Execution Time | Improvement | Key Changes |
|---------|---------------|-------------|-------------|
| Original | Xms | - | Description |
| Optimized | Yms | +Z% faster | Optimizations |

## Optimization Reasoning
[Summary of why specific optimizations were chosen]

## Recommended Query
[Optimized KQL with comments]

## Key Optimizations Applied
- List specific improvements with performance impact
- Explain why approaches were chosen over alternatives
- Document assumptions validated during testing
```

## Common Use Cases

### Query Optimization
```
"Review this KQL query and optimize it - I'm getting timeouts"
```

### Schema Validation
```
"Validate this query against Sentinel table schemas"
```

### Analytics Rule Creation
```
"Create a Sentinel rule to detect brute force using ASIM"
```

### SPL Migration
```
"Convert this Splunk detection rule to KQL"
```

### ASIM Implementation
```
"Rewrite this query to use ASIM with proper filtering"
```

### False Positive Tuning
```
"Help tune this rule using watchlists - too many false positives"
```

## Table Plan Selection

| Plan | Ingestion | Query Cost | Best For |
|------|-----------|------------|----------|
| Analytics | Standard | Free | Security data, alerts |
| Basic | ~80% lower | Per-GB | Troubleshooting |
| Auxiliary | ~90% lower | Per-GB | Compliance, audit |

## MITRE ATT&CK Coverage

This skill supports detection across all MITRE tactics:
- Initial Access, Execution, Persistence, Privilege Escalation
- Defense Evasion, Credential Access, Discovery, Lateral Movement
- Collection, Command and Control, Exfiltration, Impact

## Limitations

- KQL is read-only (no data modification)
- Max query: 10,000 characters for analytics rules
- Case-sensitive identifiers
- No dynamic workspace references
- Basic/Auxiliary tables: single table, 30-day max, no joins
- Cross-workspace: 20 max for rules, 100 for general queries

## When NOT to Use

- SQL database queries (use T-SQL)
- Azure Resource Graph (different KQL variant)
- Real-time data modification
- Dynamic workspace selection
- Non-Microsoft platforms (Splunk, Elastic)

## Version History

| Version | Changes |
|---------|---------|
| 2.2.3 | Added Robust String Parsing section warning about fragile `parse` operator; recommend `extract()` or `parse_json()` |
| 2.2.2 | Enhanced proactive triggers with specific user phrasing patterns and explicit .kql file extension detection |
| 2.2.1 | Clarified environments.json should only be accessed via schema_validator.py, not read directly |
| 2.2.0 | Added Proactive Usage section with trigger patterns and file detection guidance |
| 2.1.0 | Added Extended Thinking Framework, Query Analysis Workflow, Contains Elimination Patterns, Performance Targets, Optimization Report Template |
| 2.0.0 | Added schema_validator.py with environments.json support, reorganized to scripts/ and references/ folders |
| 1.0.0 | Initial release with optimizer, validator, patterns |

---

**Version**: 2.2.3
**Last Updated**: January 2026
