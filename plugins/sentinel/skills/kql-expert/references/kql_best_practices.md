# KQL Best Practices Reference

Comprehensive best practices for writing optimized KQL queries for Microsoft Sentinel and Azure Log Analytics.

## Table of Contents

1. [Query Performance Optimization](#query-performance-optimization)
2. [String Operations](#string-operations)
3. [Time Filtering](#time-filtering)
4. [Join Optimization](#join-optimization)
5. [Aggregation Patterns](#aggregation-patterns)
6. [Analytics Rule Development](#analytics-rule-development)
7. [ASIM Normalization](#asim-normalization)
8. [False Positive Tuning](#false-positive-tuning)
9. [Cost Optimization](#cost-optimization)
10. [Common Anti-Patterns](#common-anti-patterns)

---

## Query Performance Optimization

### Filter Early Principle (CRITICAL)

The single most important optimization: **filter immediately after the table reference**.

```kql
// BAD - Filtering after expensive operations
SecurityEvent
| extend LowercaseAccount = tolower(Account)
| join kind=inner IdentityInfo on $left.Account == $right.AccountName
| where EventID == 4625
| where TimeGenerated > ago(1h)

// GOOD - Time filter first, indexed fields second
SecurityEvent
| where TimeGenerated > ago(1h)  // Time filter FIRST
| where EventID == 4625           // Indexed field filter
| join kind=inner (
    IdentityInfo
    | where TimeGenerated > ago(1h)  // Time in subquery too
  ) on $left.Account == $right.AccountName
```

### Optimal Filter Order

1. **DateTime predicates** (leverage time-based partitioning)
2. **String/Dynamic predicates** using indexed operators
3. **Numeric predicates**

### Column Pruning

Use `project` to select only needed columns before expensive operations:

```kql
SecurityEvent
| where TimeGenerated > ago(1h)
| project TimeGenerated, Account, EventID, Computer  // Prune before join
| join kind=inner (
    IdentityInfo
    | where TimeGenerated > ago(1h)
    | project AccountName, Department
) on $left.Account == $right.AccountName
```

---

## String Operations

### Term Indexing (3+ Characters)

KQL builds term indexes for strings of 3+ alphanumeric characters. Use operators that leverage this index:

| Operator | Uses Index | Performance |
|----------|-----------|-------------|
| `has` | Yes | Fast |
| `has_cs` | Yes | Fastest |
| `hasprefix` | Yes | Fast |
| `contains` | No | Slow (full scan) |
| `contains_cs` | No | Slow |

```kql
// BAD - Full column scan
| where CommandLine contains "powershell"

// GOOD - Uses term index
| where CommandLine has "powershell"

// BEST - Case-sensitive term index
| where CommandLine has_cs "PowerShell"
```

### Case-Insensitive Comparison

```kql
// BAD - Forces computation on every row
| where tolower(Account) == "admin"

// GOOD - Native case-insensitive operator
| where Account =~ "admin"
```

### String Operator Reference

| Case-Sensitive | Case-Insensitive | Use Case |
|----------------|------------------|----------|
| `==` | `=~` | Exact match |
| `!=` | `!~` | Not equal |
| `has_cs` | `has` | Term search |
| `contains_cs` | `contains` | Substring |
| `startswith_cs` | `startswith` | Prefix |
| `endswith_cs` | `endswith` | Suffix |
| `in` | `in~` | List membership |

---

## Time Filtering

### Always Filter on TimeGenerated

```kql
// CRITICAL: Include TimeGenerated filter immediately after table
SecurityEvent
| where TimeGenerated > ago(1h)  // FIRST filter
| where EventID == 4625
```

### Time Filter in Subqueries

Time scope does NOT propagate to subqueries automatically:

```kql
// BAD - Join subquery scans full history
SecurityEvent
| where TimeGenerated > ago(1h)
| join kind=inner (IdentityInfo) on Account  // No time filter!

// GOOD - Both queries filtered
SecurityEvent
| where TimeGenerated > ago(1h)
| join kind=inner (
    IdentityInfo
    | where TimeGenerated > ago(1h)  // REQUIRED
) on $left.Account == $right.AccountName
```

### Time Range Thresholds

| Time Span | Impact |
|-----------|--------|
| < 14 days | Optimal (hot storage) |
| 14-15 days | Acceptable |
| > 15 days | Excessive resource flag |
| > 90 days | May be throttled |

### DateTime Functions

```kql
// Relative time (recommended)
| where TimeGenerated > ago(1h)
| where TimeGenerated >= ago(7d) and TimeGenerated < ago(1d)

// Absolute time (ISO 8601 format)
| where TimeGenerated >= datetime(2024-05-25T08:20:03Z)

// Time binning for aggregation
| summarize count() by bin(TimeGenerated, 1h)
```

---

## Join Optimization

### Join Strategy Hints

| Scenario | Hint | When to Use |
|----------|------|-------------|
| Small right table (<100KB) | `hint.strategy=broadcast` | Dimension lookups |
| High-cardinality keys (>1M) | `hint.shufflekey=<key>` | IP, GUID joins |
| Small dimension table | Use `lookup` instead | Auto-broadcast |

```kql
// Broadcast join for small tables
| join kind=inner hint.strategy=broadcast (
    SmallTable
    | where TimeGenerated > ago(1h)
) on Key

// Shuffle for high-cardinality keys
| join kind=inner hint.shufflekey=IPAddress (
    LargeTable
    | where TimeGenerated > ago(1h)
) on IPAddress
```

### Lookup Operator

Use `lookup` instead of `join` for dimension table lookups:

```kql
// More efficient than join for small lookup tables
SecurityEvent
| where TimeGenerated > ago(1h)
| lookup kind=leftouter (
    DimensionTable | project Key, Description
) on Key
```

### Prevent Cartesian Explosions

```kql
// BAD - Multiple matches cause row explosion
LeftTable | join RightTable on Key

// GOOD - Deduplicate before joining
LeftTable
| join (
    RightTable
    | summarize arg_max(Timestamp, *) by Key  // Deduplicate
) on Key
```

---

## Aggregation Patterns

### Use `top` Instead of `sort | take`

```kql
// BAD - Materializes full dataset
| sort by TimeGenerated desc
| take 100

// GOOD - Optimized single operation
| top 100 by TimeGenerated desc
```

### Conditional Aggregation

```kql
// Multiple conditions in single pass
| summarize
    TotalCount = count(),
    FailedCount = countif(EventResult == "Failure"),
    SuccessCount = countif(EventResult == "Success"),
    DistinctUsers = dcount(UserName)
    by bin(TimeGenerated, 1h)
```

### Approximate Distinct Count

```kql
// Exact (slower for large datasets)
| summarize ExactDistinct = dcount(UserName)

// Approximate with accuracy parameter (faster)
| summarize ApproxDistinct = dcount(UserName, 2)  // 2 = relative error ~1.8%
```

---

## Analytics Rule Development

### Required: Return TimeGenerated

```kql
// Analytics rules require TimeGenerated for lookback
SecurityEvent
| where TimeGenerated > ago(1h)
| project TimeGenerated, Account, EventID  // MUST include TimeGenerated
```

### Query Length Limit

- Maximum: 10,000 characters
- Solution: Use watchlists or functions for large lists

### Prohibited Patterns

```kql
// NEVER use in analytics rules:
search *        // Scans all tables
union *         // Scans all tables
```

### Entity Mapping Best Practices

- Limit to 3 strong identifiers for optimal grouping
- Maximum 10 entity mappings per rule
- Maximum 3 identifiers per entity
- Total entities per alert: 500 max

### Scheduling Constraints

- `queryFrequency` must be ≤ `queryPeriod`
- For lookback ≥ 2 days: frequency must be ≥ 1 hour
- NRT rules: 50 max per workspace, 30 alerts per execution

---

## ASIM Normalization

### Always Use Filtering Parameters

```kql
// BAD - No filtering, scans all data then filters
_Im_Authentication
| where TimeGenerated > ago(1h)
| where EventResult == 'Failure'

// GOOD - Filtering pushed to source tables
_Im_Authentication(
    starttime=ago(1h),
    endtime=now(),
    eventresult='Failure'
)
```

### Common ASIM Parameters

| Schema | Common Parameters |
|--------|-------------------|
| Authentication | `starttime`, `endtime`, `eventresult`, `username_has_any` |
| Network Session | `starttime`, `endtime`, `srcipaddr_has_any_prefix`, `dstipaddr_has_any_prefix` |
| DNS | `starttime`, `endtime`, `responsecodename`, `domain_has_any` |
| Process Event | `starttime`, `endtime`, `hostname_has_any`, `commandline_has_any` |

### Parser Types

| Type | Example | Use Case |
|------|---------|----------|
| Unifying (with filters) | `_Im_Authentication` | Analytics rules |
| Source-specific | `_Im_Authentication_AAD` | Workbooks |
| Parameter-less (legacy) | `_ASim_Authentication` | Avoid in production |

---

## False Positive Tuning

### Watchlist-Based Exclusions (Recommended)

```kql
// IP allowlist exclusion
let allowlist = _GetWatchlist('TrustedIPs') | project SearchKey;
SigninLogs
| where TimeGenerated > ago(1d)
| where IPAddress !in (allowlist)
```

### Subnet/CIDR Exclusions

```kql
let subnets = _GetWatchlist('CorporateSubnets');
SigninLogs
| where TimeGenerated > ago(1d)
| evaluate ipv4_lookup(subnets, IPAddress, network, return_unmatched = true)
| where isempty(network)  // Only non-corporate IPs
```

### Exception Hierarchy

1. **Automation Rules** (preferred): Recurring, expected activities; set expiration
2. **Watchlists**: Multi-rule exceptions; centralized management
3. **KQL Modifications**: Permanent, complex, or subnet-based exceptions

### Visibility Preservation

- **Avoid** hardcoding exclusions (creates blind spots)
- **Document** all exceptions with business justification
- **Set expiration dates** for temporary exceptions
- **Review** exceptions regularly

---

## Cost Optimization

### Table Plans

| Plan | Ingestion Cost | Query Cost | Best For |
|------|---------------|------------|----------|
| Analytics | Standard | Free | Security data, frequent queries |
| Basic | ~80% lower | Per-GB scan | Troubleshooting, infrequent access |
| Auxiliary | ~90% lower | Per-GB scan | Compliance, audit logs |

### Analyze Costs with KQL

```kql
// Top cost drivers by table
Usage
| where TimeGenerated > ago(30d)
| where IsBillable == true
| summarize BillableDataGB = sum(Quantity) / 1000 by DataType
| sort by BillableDataGB desc
| take 10
```

### Free Data Sources

- Azure Activity Logs
- Office 365 Audit Logs (with E5)
- Microsoft Sentinel Health
- Security alerts from Defender products
- M365 E5: 5 MB/user/day free

---

## Common Anti-Patterns

### String Operations

| Anti-Pattern | Correct Pattern |
|--------------|-----------------|
| `contains` for terms | `has` for whole terms |
| `tolower(x) == "y"` | `x =~ "y"` |
| `search *` | Explicit table name |
| `union *` | Explicit table list |

### Time Filtering

| Anti-Pattern | Correct Pattern |
|--------------|-----------------|
| No TimeGenerated filter | Always filter first |
| Time filter in subquery missing | Add to every subquery |
| >15 day spans | Limit or batch queries |

### Joins

| Anti-Pattern | Correct Pattern |
|--------------|-----------------|
| Large table on left | Small table on left |
| No join hints | Use `broadcast` or `shufflekey` |
| No time filter in subquery | Add TimeGenerated filter |

### Aggregation

| Anti-Pattern | Correct Pattern |
|--------------|-----------------|
| `sort by | take N` | `top N by` |
| Filter after summarize | Filter before summarize |
| No `project` before join | Prune columns first |

---

## Resource Thresholds

| Metric | Threshold | Impact |
|--------|-----------|--------|
| CPU time > 100s | Excessive | Warning |
| CPU time > 1,000s | Abusive | Throttled |
| Time span > 15 days | Excessive | Warning |
| Time span > 90 days | Abusive | Throttled |
| Cross-region > 3 | Excessive | Warning |
| Cross-region > 6 | Abusive | Throttled |
| Query timeout | 4 min (default) | Max 1 hour |
| Result limit | 500K records OR 64MB | Partial failure |

---

## References

- [Microsoft Learn - KQL Overview](https://learn.microsoft.com/en-us/kusto/query/)
- [Microsoft Learn - Optimize Log Queries](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/query-optimization)
- [Microsoft Learn - String Operators](https://learn.microsoft.com/en-us/kusto/query/datatypes-string-operators)
- [Microsoft Learn - ASIM Normalization](https://learn.microsoft.com/en-us/azure/sentinel/normalization)
