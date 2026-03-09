# KQL Transforms Reference for DCR Transformations

Source: https://learn.microsoft.com/en-us/azure/azure-monitor/essentials/data-collection-transformations-kql

## Core Rules
- Transformations apply to **each record individually** — no multi-record operators
- Only operators listed here are supported — everything else is blocked
- `parse` limited to **10 columns per statement** — chain multiple statements for more
- Transforms taking **>20 seconds** may cause data loss — target <1 second
- Every transform must produce a `TimeGenerated` column (datetime)
- No blank lines in `transformKql` strings
- Escape quotes in JSON: `\"` inside the transformKql string value

## Supported Tabular Operators
| Operator | Supported | Notes |
|----------|-----------|-------|
| `source` | Yes | Required data source reference |
| `print` | Yes | Produces a single row |
| `let` | Yes | Scalar, tabular, or user-defined functions (scalar args only) |
| `where` | Yes | Filter rows |
| `extend` | Yes | Add/calculate columns |
| `project` | Yes | Select and rename columns |
| `project-away` | Yes | Remove columns |
| `project-rename` | Yes | Rename columns |
| `parse` | Yes | **Max 10 output columns per statement** |
| `datatable` | Yes | Inline reference data |
| `columnifexists` | Yes | Safe column access |

## Blocked Tabular Operators
`summarize`, `join`, `union`, `mv-expand`, `mv-apply`, `top`, `sort`, `distinct`, `invoke`, `scan`, `partition`, `project-reorder`, `parse_csv`

## Supported String Operators
| Operator | Description |
|----------|-------------|
| `==` | Equals |
| `!=` | Not equals |
| `=~` | Equals (case-insensitive) |
| `!~` | Not equals (case-insensitive) |
| `contains` / `!contains` | Substring match |
| `contains_cs` / `!contains_cs` | Substring match (case-sensitive) |
| `has` / `!has` | Whole-term match |
| `has_cs` / `!has_cs` | Whole-term match (case-sensitive) |
| `startswith` / `!startswith` | Prefix match |
| `startswith_cs` / `!startswith_cs` | Prefix match (case-sensitive) |
| `endswith` / `!endswith` | Suffix match |
| `endswith_cs` / `!endswith_cs` | Suffix match (case-sensitive) |
| `matches regex` | Regex match |
| `in` / `!in` | Set membership |

## Supported Scalar Functions

### Type Conversion
`tostring`, `toint`, `tolong`, `todouble`/`toreal`, `todatetime`, `totimespan`, `tobool`, `toguid`

### Math & Rounding
`abs`, `round`, `floor`/`bin`, `ceiling`, `log`, `log10`, `log2`, `exp`, `exp10`, `exp2`, `pow`, `sign`

### Bitwise
`binary_and`, `binary_or`, `binary_not`, `binary_xor`, `binary_shift_left`, `binary_shift_right`

### Conditional
`iif`, `case`, `max_of`, `min_of`

### Type Checking
`isnull`, `isnotnull`, `isfinite`, `isinf`, `isnan`, `gettype`

### DateTime / Timespan
`now`, `ago`, `startofday`, `endofday`, `startofweek`, `endofweek`, `startofmonth`, `endofmonth`, `startofyear`, `endofyear`, `datetime_add`, `datetime_diff`, `datetime_part`, `hourofday`, `dayofweek`, `dayofmonth`, `dayofyear`, `weekofyear`, `getmonth`, `getyear`, `make_datetime`, `make_timespan`, `todatetime`, `totimespan`

### String Functions
`strcat`, `strcat_delim`, `substring`, `strlen`, `split`, `tolower`, `toupper`, `indexof`, `extract`, `extract_all`, `countof`, `hash_sha256`, `base64_encodestring`, `base64_decodestring`, `isempty`, `isnotempty`, `parse_json`

### Dynamic / Array / JSON
`parse_json`, `parse_xml`, `pack`, `pack_array`, `array_length`, `array_concat`, `zip`

### Special (DCR-only)
`geo_location` — IP geolocation (IPv4/IPv6). Returns country, region, state, city, lat, long. **Adds ingestion latency — use sparingly.**

`parse_cef_dictionary` — Parses CEF message Extension property into dynamic key/value. Replace semicolons before calling.

## Blocked Functions
| Function | Alternative |
|----------|-------------|
| `coalesce` | `iif(isnotnull(a), a, b)` |
| `replace_string` | Use `extract` with regex, or `parse` |
| `replace_regex` | Use `extract` with regex, or `parse` |
| `bag_keys` | Not available — restructure with explicit `pack()` |
| `bag_values` | Not available |
| `bag_set` | Not available |
| `bag_remove_keys` | Use explicit `pack()` or `project` to include only needed fields |
| `dynamic()` literal | `parse_json('{"key":"value"}')` |
| `dynamic([])` | `pack_array()` |
| `pack()` zero args | `parse_json("{}")` |

## Common Transform Patterns

### Pass-through (no transform)
```
source
```

### Add TimeGenerated from source field
```
source | extend TimeGenerated = todatetime(ts)
```

### Add TimeGenerated as current time
```
source | extend TimeGenerated = now()
```

### Filter and project
```
source | where eventType == "Alert" | project TimeGenerated = todatetime(ts), SourceIP = srcIp, Message = message
```

### Parse nested JSON
```
source | extend parsed = parse_json(rawData) | extend TimeGenerated = todatetime(parsed.timestamp), User = tostring(parsed.user.name)
```

### Split to multiple tables (use separate dataFlows with different outputStream values)
DataFlow 1: `source | where eventType == "Alert" | project TimeGenerated = ts, ...`
DataFlow 2: `source | where eventType == "File" | project-rename TimeGenerated = ts, ...`

### Coalesce replacement
```
source | extend result = iif(isnotnull(fieldA), fieldA, fieldB)
```

### Dynamic literal replacement
```
source | extend emptyObj = parse_json("{}") | extend emptyArr = pack_array()
```

### Inline lookup table
```
source | extend severityMap = parse_json('{"1":"Low","2":"Medium","3":"High"}') | extend SeverityLabel = tostring(severityMap[tostring(severityLevel)])
```

## Testing Transforms
1. Pull real data from source API via PowerShell/curl
2. Create a `datatable` in Log Analytics mimicking the incoming stream schema
3. Test your KQL transform against the datatable
4. Copy working KQL (without datatable) into the DCR `transformKql`

## Performance Best Practices
- Filter early with `where` to reduce processing volume
- Avoid complex string operations on large fields
- Truncate large fields: `substring(Message, 0, 1000)`
- Keep transforms simple — under 1 second execution
- Multiple `parse` statements are better than one massive transform
