# Best Practices and Rules for KQL in Data Collection Rule Transformations

Data Collection Rules (DCRs) in Azure Monitor allow organisations to filter and modify incoming log data before it is stored in a Log Analytics workspace. The Kusto Query Language (KQL) used within DCR transformations has specific limitations compared to standard KQL used in Log Analytics queries. This guide outlines the supported features, known limitations, and best practices for writing effective DCR transformation queries.

> **Scope**: All guidance in this document applies specifically to KQL within DCR transformations. General Log Analytics query optimisation techniques do not apply here.

---

## Core Transformation Concepts

Transformations in a DCR apply a KQL query to each individual record before it is stored in a Log Analytics workspace. The transformation must produce output that matches the schema of the target table. Columns not included in the transformation output will be empty in the target table — you do not need to include every target column.

The input stream is represented by a virtual table named `source`, with columns matching the input data stream definition.

Most Log Analytics target tables require a column called `TimeGenerated` of type `datetime`. This is a schema requirement of the target table, not a universal KQL rule — but it applies to the vast majority of standard tables. If your source data does not include this field, add it explicitly using `extend` or `project`:

```kusto
source | extend TimeGenerated = now()
```

A typical transformation query follows this pattern:

```kusto
source
| where [filtering conditions]
| extend [additional columns]
| project [output columns including TimeGenerated]
```

---

## KQL Limitations in DCR Transformations

Since transformations are applied to each record individually, only operators that take a single row as input and return no more than one row are supported. Operators that act on multiple records are not supported.

> **Important**: Only the operators and functions explicitly listed below are supported. Any operator or function not on these lists will not work in a DCR transformation, regardless of whether it works in standard Log Analytics queries.

### Supported Tabular Operators

| Operator | Purpose |
|---|---|
| `where` | Filter records |
| `extend` | Add or modify columns |
| `project` | Select specific output columns |
| `project-away` | Exclude specific columns |
| `project-rename` | Rename columns |
| `parse` | Extract values from strings into named columns |
| `print` | Produce a single static row (also valid as a data source) |
| `datatable` | Define an inline table of constant values |
| `columnifexists` | Reference a column only if it exists in the input stream |

> **Naming warning**: Use `columnifexists` — not `column_ifexists`. The underscore form is not supported and will produce an error.

### Supported Statements

**`let` statement**: The right-hand side of a `let` statement can be a scalar expression, a tabular expression, or a user-defined function. Only user-defined functions with scalar arguments are supported — tabular user-defined functions are not.

### Data Sources in a Transformation

The only supported data sources within a DCR transformation query are:

- **`source`** — the incoming record stream
- **`print`** — produces a single constant row, useful for generating static output

### Unsupported Operators

The following commonly used KQL operators are not supported in DCR transformations:

- `summarize` — aggregation across multiple records
- `join` — combining data from multiple sources
- `union` — combining results from multiple queries
- `top` — selecting a fixed number of records

---

## Supported Scalar Operators

### String Operators

The following string operators are supported:

`==`, `!=`, `=~`, `!~`, `contains`, `!contains`, `contains_cs`, `!contains_cs`, `has`, `!has`, `has_cs`, `!has_cs`, `startswith`, `!startswith`, `startswith_cs`, `!startswith_cs`, `endswith`, `!endswith`, `endswith_cs`, `!endswith_cs`, `matches regex`, `in`, `!in`

> **Note**: Use these as operators in expressions (e.g., `where RawData startswith "{"`) — not as function calls (e.g., `startswith(RawData, "{")` is incorrect syntax in this context).

### Other Operators

- All numerical operators are supported.
- All datetime and timespan arithmetic operators are supported.
- Bitwise operators: `binary_and()`, `binary_or()`, `binary_xor()`, `binary_not()`, `binary_shift_left()`, `binary_shift_right()`

---

## Supported Scalar Functions

Only functions in the following list are supported. Functions not listed here — including `coalesce()`, `bag_remove_keys()`, and others common in standard KQL — are **not supported** in DCR transformations.

### Conversion
`tobool`, `todatetime`, `todouble`/`toreal`, `toguid`, `toint`, `tolong`, `tostring`, `totimespan`

### Conditional
`case`, `iif`, `max_of`, `min_of`

### String
`base64_encodestring`, `base64_decodestring`, `countof`, `extract`, `extract_all`, `indexof`, `isempty`, `isnotempty`, `parse_json`, `split`, `strcat`, `strcat_delim`, `strlen`, `substring`, `tolower`, `toupper`, `hash_sha256`

> **Naming warning**: Use `base64_encodestring` and `base64_decodestring` — not `base64_encode_tostring` or `base64_decode_tostring`. The `_tostring` variants are not supported.

> **Note on string replacement**: `replace_string` is used in Microsoft's official sample documentation but does not appear on the formal supported functions allowlist. `replace` (argument order: `replace(pattern, rewrite, source)`) is used in Microsoft's own `parse_cef_dictionary` reference example. Both appear to work in practice — verify against current Microsoft documentation before relying on either in production.

### Dynamic and Array
`array_concat`, `array_length`, `pack_array`, `pack`, `parse_json`, `parse_xml`, `zip`

> **Note**: `parse_json` also appears in the String functions category above because it accepts a string argument. It is listed here as its primary use is constructing and returning dynamic objects.

### DateTime and TimeSpan
`ago`, `datetime_add`, `datetime_diff`, `datetime_part`, `dayofmonth`, `dayofweek`, `dayofyear`, `endofday`, `endofmonth`, `endofweek`, `endofyear`, `getmonth`, `getyear`, `hourofday`, `make_datetime`, `make_timespan`, `now`, `startofday`, `startofmonth`, `startofweek`, `startofyear`, `todatetime`, `totimespan`, `weekofyear`

### Mathematical
`abs`, `bin`/`floor`, `ceiling`, `exp`, `exp10`, `exp2`, `isfinite`, `isinf`, `isnan`, `log`, `log10`, `log2`, `pow`, `round`, `sign`

### Bitwise
`binary_and`, `binary_or`, `binary_not`, `binary_shift_left`, `binary_shift_right`, `binary_xor`

### Type
`gettype`, `isnotnull`, `isnull`

---

## Special Transformation-Only Functions

The following functions are **only available in DCR transformations**. They cannot be used in standard Log Analytics queries.

### `parse_cef_dictionary`

Parses the Extension property of a CEF message string into a dynamic key/value object.

> **Important**: Semicolons are reserved characters in CEF and must be replaced before passing the message to this function.

```kusto
source
| extend cefMessage = iff(cefMessage contains_cs ";", replace(";", " ", cefMessage), cefMessage)
| extend parsedCefDictionaryMessage = parse_cef_dictionary(cefMessage)
| extend parsedExtension = parsedCefDictionaryMessage["Extension"]
| project TimeGenerated, cefMessage, parsedExtension
```

> **Note**: This example uses `replace(pattern, rewrite, source)` and `iff`, matching the official Microsoft reference exactly. `replace` is not on the formal supported functions allowlist but is used in Microsoft's own documentation for this function.

### `geo_location`

Returns approximate geographical location for an IP address (IPv4 and IPv6). Returns a dynamic object containing Country, Region, State, City, Latitude, and Longitude.

```kusto
source
| extend GeoLocation = geo_location(ClientIP)
```

> **Important**: This function uses an IP geolocation service and can introduce data ingestion latency if called excessively. Exercise caution when using it more than several times per transformation.

---

## Working with Dynamic Data

### Dynamic Literals

Use `parse_json` instead of `dynamic()` literal syntax. The two forms are equivalent, but `parse_json` is the supported form in DCR transformations:

```kusto
// Use this form
extend myObj = parse_json('{"key":"value","count":42}')

// Equivalent to — but prefer parse_json in DCR transformations
extend myObj = dynamic({"key":"value","count":42})
```

### Constructing Dynamic Objects and Arrays at Runtime

Use `pack()` to construct a dynamic bag from key-value pairs, and `pack_array()` to construct a dynamic array:

```kusto
// Construct a dynamic object from runtime values
extend summary = pack("host", Computer, "level", Level, "code", EventID)

// Construct an array from runtime values
extend tags = pack_array("critical", "reviewed")

// Empty bag or empty array
extend emptyObject = pack()
extend emptyArray = pack_array()
```

### Accessing Properties of Dynamic Columns

Define the column as type `dynamic` in the input stream definition, then use `parse_json` to access nested properties:

```kusto
source
| extend parsed = parse_json(AdditionalContext)
| extend Level = toint(parsed.Level)
| extend DeviceId = tostring(parsed.DeviceID)
```

### Handling Potentially Malformed JSON

```kusto
source
| extend parsedData = iif(
    isnotempty(RawData),
    iif(
        RawData startswith "{",
        parse_json(RawData),
        pack("raw", RawData)
    ),
    pack()
)
```

---

## Null and Empty Value Handling

`coalesce()` is not in the supported scalar function list and is not supported in DCR transformations. Use `iif` with `isnotnull` or `isnotempty` instead:

```kusto
// coalesce() is not supported — use iif with isnotnull
extend safeValue = iif(isnotnull(possiblyNullValue), possiblyNullValue, "default")

// For empty strings, use isnotempty
extend safeValue = iif(isnotempty(possiblyEmptyValue), possiblyEmptyValue, "default")
```

---

## The `parse` Operator

The `parse` operator is supported in DCR transformations but is limited to **10 column extractions per statement**. If you need to extract more than 10 columns, split into multiple `parse` statements:

```kusto
// First 5 fields
source
| parse Message with * "field1=" Field1: string " field2=" Field2: string " field3=" Field3: string " field4=" Field4: string " field5=" Field5: string *
// Next fields in a second statement
| parse Message with * " field6=" Field6: string " field7=" Field7: string " field8=" Field8: string " field9=" Field9: string " field10=" Field10: string *
```

---

## Removing Unsupported Functions

### `bag_remove_keys` Is Not Supported

`bag_remove_keys()` is not in the supported function list. To remove specific keys from a dynamic bag, reconstruct it using `pack()` with only the keys you want to keep:

```kusto
// bag_remove_keys() is not supported
// Reconstruct the bag with only the keys you want
extend properties_safe = pack(
    "key1", properties.key1,
    "key2", properties.key2
)
```

---

## Practical Examples

### Filter Rows

```kusto
source | where severity == "Critical"
```

### Filter Columns

```kusto
source | project-away RawData
```

### Remove Sensitive Columns

```kusto
source | project-away ClientIP
```

### Obfuscate Sensitive Data

Use `replace_string` with `substring` and `indexof` to mask part of a field value. Note that `replace_string` appears in Microsoft's official sample documentation for this pattern, though it is not formally enumerated on the supported functions allowlist:

```kusto
source
| extend Email = replace_string(Email, substring(Email, 0, indexof(Email, "@")), "*****")
```

### Parse JSON and Extract Fields

```kusto
source
| extend Context = parse_json(RequestContext)
| extend WorkspacePath = tostring(Context['workspaces'][0])
| extend WorkspaceName = tostring(split(WorkspacePath, "/")[8])
| project-away RequestContext, Context, WorkspacePath
```

### Enrich Data

```kusto
source
| extend IpLocation = iif(split(ClientIp, ".")[0] in ("10", "192"), "Internal", "External")
```

### Normalize Data to ASIM Schema

```kusto
source
| project
    TimeGenerated = timestamp,
    EventOwner = owner,
    EventMessage = message,
    EventResult = result,
    EventSeverity = severity
```

### Parse a Comma-Delimited Field

```kusto
source
| project d = split(RawData, ",")
| project
    TimeGenerated = todatetime(d[0]),
    Code = toint(d[1]),
    Severity = tostring(d[2]),
    Module = tostring(d[3]),
    Message = tostring(d[4])
```

### Add Geographic Enrichment

```kusto
source
| extend GeoLocation = geo_location(ClientIP)
| extend Country = tostring(GeoLocation.Country)
| extend City = tostring(GeoLocation.City)
```

### Parse CEF Security Logs

```kusto
source
| extend cefMessage = iff(RawData contains_cs ";", replace(";", " ", RawData), RawData)
| extend parsed = parse_cef_dictionary(cefMessage)
| extend Extension = parsed["Extension"]
| project TimeGenerated, RawData, Extension
```

---

## Best Practices

1. **Filter early**: Place `where` operators as early as possible in the query to reduce the amount of data processed by subsequent steps.
2. **Use the allowlist, not assumptions**: If a function or operator is not in the supported lists in this document, assume it is not supported — test before deploying.
3. **Handle nulls explicitly**: Use `iif(isnotnull(...), ..., ...)` or `iif(isnotempty(...), ..., ...)` instead of `coalesce()`.
4. **Use `parse_json` for dynamic literals**: Prefer `parse_json('...')` over `dynamic(...)` literal syntax in DCR transformations.
5. **Use `columnifexists` for optional fields**: When the presence of a column in the input stream is uncertain, use `columnifexists` to avoid errors. Do not use `column_ifexists`.
6. **Split large `parse` statements**: Keep each `parse` statement to 10 or fewer column extractions.
7. **Use `geo_location` sparingly**: Excessive calls per transformation can introduce ingestion latency.
8. **Pre-process CEF messages**: Replace semicolons before passing CEF strings to `parse_cef_dictionary`.
9. **Test transformations before deployment**: Validate with representative data before applying to a production DCR.
10. **Keep transformations simple**: Each transformation executes for every incoming record. Complex logic compounds at scale.

---

## References

1. [Supported KQL features in Azure Monitor transformations](https://learn.microsoft.com/en-us/azure/azure-monitor/essentials/data-collection-transformations-kql)
2. [Sample transformations in Azure Monitor](https://learn.microsoft.com/en-us/azure/azure-monitor/essentials/data-collection-transformations-samples)
3. [Transformations in Azure Monitor](https://learn.microsoft.com/en-us/azure/azure-monitor/essentials/data-collection-transformations)
4. [Create a transformation in Azure Monitor](https://learn.microsoft.com/en-us/azure/azure-monitor/essentials/data-collection-transformations-create)
