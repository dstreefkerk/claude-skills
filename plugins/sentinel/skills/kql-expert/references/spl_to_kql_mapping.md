# SPL to KQL Migration Reference

Command mapping and conversion guide for migrating Splunk Search Processing Language (SPL) queries to Kusto Query Language (KQL) for Microsoft Sentinel.

## Fundamental Differences

| Aspect | SPL | KQL |
|--------|-----|-----|
| Data Model | Events with fields | Tables with columns |
| Case Sensitivity | Case-insensitive | Case-sensitive |
| String Indexing | 1-based | 0-based |
| Write Operations | Supported | Read-only |
| Real-time | Continuous | Scheduled (min 5 min) |

---

## Core Search & Filter Commands

### Search/Where

| SPL | KQL | Notes |
|-----|-----|-------|
| `search index=main error` | `TableName \| where Field has "error"` | Use `has` for term search |
| `search field=value` | `\| where field == "value"` | Case-sensitive `==` |
| `search field=value (case-insensitive)` | `\| where field =~ "value"` | Explicit case-insensitive |
| `search field IN (a, b, c)` | `\| where field in ("a", "b", "c")` | Case-sensitive list |
| `search field!=value` | `\| where field != "value"` | Not equal |
| `search field="*partial*"` | `\| where field contains "partial"` | Substring match |
| `search field="prefix*"` | `\| where field startswith "prefix"` | Prefix match |

### Wildcards

| SPL | KQL | Notes |
|-----|-----|-------|
| `field="*"` | `\| where isnotempty(field)` | Any non-empty value |
| `field="value*"` | `\| where field startswith "value"` | Prefix |
| `field="*value"` | `\| where field endswith "value"` | Suffix |
| `field="*val*"` | `\| where field contains "val"` | Substring |

---

## Data Transformation Commands

### eval -> extend

| SPL | KQL | Notes |
|-----|-----|-------|
| `eval new_field=field1 + field2` | `\| extend new_field = field1 + field2` | Numeric addition |
| `eval fullname=first." ".last` | `\| extend fullname = strcat(first, " ", last)` | String concatenation |
| `eval upper_name=upper(name)` | `\| extend upper_name = toupper(name)` | String functions |
| `eval len=len(field)` | `\| extend len = strlen(field)` | String length |
| `eval result=if(x>0,"yes","no")` | `\| extend result = iff(x>0, "yes", "no")` | Conditional (note: `iff` not `if`) |

### table/fields -> project

| SPL | KQL | Notes |
|-----|-----|-------|
| `table field1, field2` | `\| project field1, field2` | Select columns |
| `fields - field1` | `\| project-away field1` | Remove columns |
| `fields + field1` | `\| project-reorder field1` | Reorder columns |

### rename -> project-rename

| SPL | KQL | Notes |
|-----|-----|-------|
| `rename old AS new` | `\| project-rename new = old` | Uses `=` not `AS` |
| `rename old1 AS new1, old2 AS new2` | `\| project-rename new1 = old1, new2 = old2` | Multiple renames |

### rex -> parse/extract

| SPL | KQL | Notes |
|-----|-----|-------|
| `rex field=msg "user=(?<user>\w+)"` | `\| extend user = extract("user=(\\w+)", 1, msg)` | Regex extraction |
| `rex field=msg "(?<key>\w+)=(?<val>\w+)"` | `\| parse msg with * "=" key:string "=" val:string` | Pattern parsing |

---

## Aggregation Commands

### stats -> summarize

| SPL | KQL | Notes |
|-----|-----|-------|
| `stats count` | `\| summarize count()` | Total count |
| `stats count by field` | `\| summarize count() by field` | Group count |
| `stats count as cnt by field` | `\| summarize cnt = count() by field` | Named aggregation |
| `stats dc(field)` | `\| summarize dcount(field)` | Distinct count |
| `stats sum(field)` | `\| summarize sum(field)` | Sum |
| `stats avg(field)` | `\| summarize avg(field)` | Average |
| `stats min(field)` | `\| summarize min(field)` | Minimum |
| `stats max(field)` | `\| summarize max(field)` | Maximum |
| `stats values(field)` | `\| summarize make_set(field)` | Distinct values |
| `stats list(field)` | `\| summarize make_list(field)` | All values |
| `stats earliest(_time)` | `\| summarize arg_min(TimeGenerated, *)` | Row with min time |
| `stats latest(_time)` | `\| summarize arg_max(TimeGenerated, *)` | Row with max time |
| `stats first(field)` | `\| summarize take_any(field)` | Any value |

### timechart -> summarize + bin + render

| SPL | KQL | Notes |
|-----|-----|-------|
| `timechart span=1h count` | `\| summarize count() by bin(TimeGenerated, 1h) \| render timechart` | Time series |
| `timechart span=1d avg(value) by type` | `\| summarize avg(value) by bin(TimeGenerated, 1d), type \| render timechart` | Grouped time series |

### top/rare

| SPL | KQL | Notes |
|-----|-----|-------|
| `top 10 field` | `\| summarize count() by field \| top 10 by count_` | Top N by count |
| `rare field` | `\| summarize count() by field \| sort by count_ asc \| take 10` | Bottom N |

---

## Join & Lookup Commands

### join

| SPL | KQL | Notes |
|-----|-----|-------|
| `join type=inner field [search ...]` | `\| join kind=inner (Table2 \| where ...) on field` | Inner join |
| `join type=left field [search ...]` | `\| join kind=leftouter (Table2 \| where ...) on field` | Left outer join |
| `join type=outer field [search ...]` | `\| join kind=fullouter (Table2 \| where ...) on field` | Full outer join |

### lookup -> lookup/join with watchlist

| SPL | KQL | Notes |
|-----|-----|-------|
| `lookup users.csv username OUTPUT fullname` | `\| lookup kind=leftouter (_GetWatchlist('users') \| project SearchKey, fullname) on $left.username == $right.SearchKey` | Watchlist lookup |
| `inputlookup users.csv` | `_GetWatchlist('users')` | Load lookup table |

**Note**: SPL `outputlookup` has no KQL equivalent (KQL is read-only).

---

## Time & Date Functions

| SPL | KQL | Notes |
|-----|-----|-------|
| `earliest=-1h` | `\| where TimeGenerated > ago(1h)` | Relative time |
| `earliest=-7d@d` | `\| where TimeGenerated >= startofday(ago(7d))` | Snap to day |
| `strftime(_time, "%Y-%m-%d")` | `format_datetime(TimeGenerated, "yyyy-MM-dd")` | Format datetime |
| `strptime(field, "%Y-%m-%d")` | `todatetime(field)` | Parse datetime |
| `relative_time(now(), "-1d@d")` | `startofday(ago(1d))` | Relative with snap |

### Time Span Units

| SPL | KQL |
|-----|-----|
| `1s` | `1s` |
| `1m` | `1m` |
| `1h` | `1h` |
| `1d` | `1d` |
| `1w` | `7d` |
| `1mon` | `30d` (approximate) |

---

## String Functions

| SPL | KQL | Notes |
|-----|-----|-------|
| `len(field)` | `strlen(field)` | String length |
| `substr(field, 1, 5)` | `substring(field, 0, 5)` | **KQL is 0-based!** |
| `upper(field)` | `toupper(field)` | Uppercase |
| `lower(field)` | `tolower(field)` | Lowercase |
| `trim(field)` | `trim(' ', field)` | Trim whitespace |
| `ltrim(field)` | `trim_start(' ', field)` | Left trim |
| `rtrim(field)` | `trim_end(' ', field)` | Right trim |
| `replace(field, "old", "new")` | `replace(field, "old", "new")` | Replace string |
| `split(field, ",")` | `split(field, ",")` | Split to array |
| `mvindex(field, 0)` | `tostring(split(field, ",")[0])` | Array element |

---

## Network Functions

| SPL | KQL | Notes |
|-----|-----|-------|
| `cidrmatch("10.0.0.0/8", ip)` | `ipv4_is_match(ip, "10.0.0.0", 8)` | CIDR match |
| `iplocation(ip)` | `geo_info_from_ip_address(ip)` | IP geolocation |

---

## Conditional Logic

| SPL | KQL | Notes |
|-----|-----|-------|
| `if(condition, true, false)` | `iff(condition, true, false)` | Note extra 'f' |
| `case(cond1, val1, cond2, val2, default)` | `case(cond1, val1, cond2, val2, default)` | Multi-condition |
| `coalesce(a, b, c)` | `coalesce(a, b, c)` | First non-null |
| `isnull(field)` | `isnull(field)` | Null check |
| `isnotnull(field)` | `isnotnull(field)` | Not null check |
| `isempty(field)` | `isempty(field)` | Empty string check |

---

## Sorting & Limiting

| SPL | KQL | Notes |
|-----|-----|-------|
| `sort -field` | `\| sort by field desc` | Descending sort |
| `sort +field` | `\| sort by field asc` | Ascending sort |
| `head 10` | `\| take 10` | Limit results |
| `tail 10` | `\| top 10 by TimeGenerated asc` | Last N records |
| `dedup field` | `\| summarize arg_max(TimeGenerated, *) by field` | Deduplicate |

---

## Advanced Patterns

### Transaction -> row_window_session

SPL transaction correlates events with time constraints:

```splunk
transaction user maxspan=1h maxpause=5m
```

KQL equivalent using session windows:

```kql
SecurityEvent
| where TimeGenerated > ago(1d)
| sort by Account, TimeGenerated asc
| extend SessionId = row_window_session(TimeGenerated, 1h, 5m, Account != prev(Account))
| summarize
    StartTime = min(TimeGenerated),
    EndTime = max(TimeGenerated),
    EventCount = count(),
    Events = make_list(EventID)
    by Account, SessionId
```

**Note**: Behavior differs - `row_window_session` uses session semantics, not transaction boundaries.

### Subsearch -> let statement

```splunk
index=main [search index=users role=admin | fields username]
```

```kql
let admins = UserTable | where role == "admin" | project username;
SecurityEvent
| where TimeGenerated > ago(1h)
| where Account in (admins)
```

### append -> union

```splunk
search index=main error
| append [search index=errors warning]
```

```kql
union
(MainTable | where TimeGenerated > ago(1h) | where message has "error"),
(ErrorsTable | where TimeGenerated > ago(1h) | where message has "warning")
```

---

## What Doesn't Translate

| SPL Feature | KQL Alternative | Notes |
|-------------|-----------------|-------|
| `outputlookup` | Watchlists (manual) | KQL is read-only |
| Real-time search | NRT rules (1 min) | Minimum 1 minute delay |
| `transaction` | `row_window_session` | Different behavior |
| `collect` | No equivalent | KQL is read-only |
| `sendemail` | Logic Apps/Playbooks | External automation |
| Acceleration | Materialized views | Different mechanism |

---

## Migration Checklist

1. **Audit existing SPL rules** - Focus on rules that fired in last 6-12 months
2. **Map CIM to ASIM** - Use schema mapping for data model alignment
3. **Convert syntax** - Use this reference for command mapping
4. **Validate time handling** - Ensure TimeGenerated filters are present
5. **Test in parallel** - Run Splunk and Sentinel side-by-side during transition
6. **Create watchlists** - Pre-create watchlists for any Splunk lookups
7. **Compare alert volumes** - Validate detection accuracy

---

## References

- [Microsoft Sentinel SIEM Migration](https://learn.microsoft.com/en-us/azure/sentinel/migration-splunk-detection-rules)
- [Azure Sentinel SPL to KQL Mapping](https://github.com/Azure/Azure-Sentinel/blob/master/Tools/RuleMigration/SPL%20to%20KQL.md)
