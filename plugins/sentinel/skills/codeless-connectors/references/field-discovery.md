# Field Discovery & Column Definition

Rules for mapping vendor API responses to Log Analytics table columns. Anti-hallucination
guidance for column inventory — applies whenever a new custom table is being designed.

Source: distilled from Microsoft's `@sentinel /create-connector` agent prompts shipped
in the `ms-security.ms-sentinel` VS Code extension v2.2.0 (specialist roles 06, 03, 12).

---

## The three documentation sources — always look for all of them

For any vendor API, three doc types may exist. Each gives a different view of the response
shape, and using all three together produces the most complete column inventory:

| Source type | Example | Purpose |
|-------------|---------|---------|
| **Machine-readable spec** | `openapi.json`, `swagger.yaml`, `postman_collection.json` | Authoritative response schema, all properties |
| **Event/field catalog page** | "Events for your enterprise", "Audit log events", "Event reference", "Schema reference" | Per-event-type field annotations — usually the **most complete** field source |
| **Human-readable API reference** | "REST API Reference" web page | Field descriptions, examples, edge cases |

### Doc acquisition order

1. Spec file URLs first
2. Event catalog URLs second
3. General docs last

### Resolving spec references on landing pages

Don't stop at "about the spec" pages or repo landing pages — follow through to the actual file:

- **GitHub repo link** (`github.com/{owner}/{repo}`): construct the raw URL
  `https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path-to-spec.json}`
- **Doc page about the spec**: look for direct download/file URLs on that page
- **Verify it's a spec, not HTML**: trim leading whitespace and any UTF-8 BOM, then check
  the first non-whitespace character is `{` (JSON), or starts with `openapi:`/`swagger:`/`---` (YAML).
  If you get HTML, keep following links.

### The event catalog pattern — why it matters

For log, event, and audit APIs, the OpenAPI/Swagger spec typically defines only a generic
response wrapper with a few common fields. The complete field inventory lives on a separate
documentation page that lists every event type with a per-event `Fields:` annotation.

These pages often contain **100–400+ unique fields** when you take the union across all
event types. They are the most valuable single source for column discovery for SIEM
connectors and are commonly overlooked in favour of the spec.

**Recognition heuristic:** the page has many sections (one per event type), each with a
field list like `Fields: @timestamp, _document_id, action, actor, ...`. Different event
types have different field sets — extract the UNION of all field names across all sections.

---

## Never invent columns

> **Critical rule:** Only create columns for fields you can verify exist in documentation,
> API specs, or example responses. If you cannot point to the source that proves a field
> exists, do not include it.

It is better to have fewer verified columns than many guessed ones. For a SIEM connector,
dropped fields are security blind spots — but invented fields are *worse* because they
look real and never populate.

**Self-audit gate:** before writing the columns array, walk every column you've added and
trace it back to a specific source (spec property line, doc field-list entry, example
response key). Remove any column you cannot place.

---

## Forbidden column patterns

### Catchall columns — REMOVE if present

Never create a column whose purpose is to bundle multiple fields into one without specific
documentation. Forbidden names:

```
RawEventData, EventRawData, RawData, EventData, FullEvent, AllFields,
Payload, Data, AdditionalData, ExtraFields, Properties, Details, Body,
Content, RawJson
```

A legitimate documented object/array field mapped to `dynamic` is fine — what's forbidden
is a synthetic column you created to "hold the rest."

### Pagination / response-envelope metadata — NOT event columns

Response envelope fields are not event data. Do not create columns for any of:

```
offset, limit, total, hasMore, count, page, nextPage, cursor, continuation,
pageCount, rateLimit, X-RateLimit-Remaining
```

Only create columns for fields that appear **inside** the event objects extracted by
`eventsJsonPaths`. Verify by checking the JSONPath: anything outside that path is envelope.

### Reserved Azure Monitor column names

These are populated by Azure Monitor itself — never declare them in your schema:

```
TenantId, Type, _TimeReceived, _ItemId, _ResourceId, _SubscriptionId,
_IsBillable, _BilledSize, SourceSystem, MG, ManagementGroupName,
Computer, RawData
```

Note: `TimeGenerated` is **required** (not reserved) — always include it as the first
column with type `datetime`.

### KQL-keyword collisions — rename to avoid bracket notation

Log Analytics tables are queried with KQL. Column names that collide with KQL operators
force users to write `['ColumnName']` in every query. Rename the column when mapping:

| API field | Renamed column |
|-----------|---------------|
| `project`  | `ProjectName`  |
| `title`    | `EventTitle`   |
| `count`    | `EventCount`   |
| `order`    | `OrderValue`   |

Other KQL keywords to watch for: `where`, `extend`, `join`, `let`, `search`, `union`,
`filter`, `summarize`, `sort`, `parse`, `limit`, `top`, `take`, `set`, `print`, `render`,
`invoke`, `find`, `fork`, `scan`, `reduce`, `sample`, `distinct`, `evaluate`, `lookup`,
`materialize`, `serialize`, `partition`, `consume`, `between`, `in`, `of`, `to`, `not`,
`and`, `or`, `has`, `contains`, `startswith`.

---

## API value → Log Analytics type mapping

The full Log Analytics column-type enum (from `table.schema.json`) is:
`string, int, long, real, boolean, datetime, dynamic, guid, timespan`. Map API values
as follows:

| API value example                          | Column type |
|--------------------------------------------|-------------|
| `"text value"`                             | `string`    |
| `42`, `9876543210` (any integer)           | `real`      |
| `3.14` (decimal)                           | `real`      |
| `true` / `false`                           | `boolean`   |
| `"2024-01-15T10:30:00Z"`                   | `datetime`  |
| `[...]` (array)                            | `dynamic`   |
| `{...}` (nested object)                    | `dynamic`   |
| `"550e8400-e29b-41d4-..."` (UUID)          | `guid`      |
| `"PT15M"`, `"01:30:00"` (ISO 8601 duration / timespan) | `timespan`  |

**Use `real` for all numbers**, including integers. The legacy `int`/`long` types still
work but `real` is the agent's default and avoids overflow on large integer IDs (snowflake
IDs, epoch nanoseconds).

### dataTypeHint — semantic hint for query optimisation

Beyond `type`, each column can declare an optional `dataTypeHint` to give Log Analytics a
semantic hint that improves query performance and surfaces semantic features in the UI
(geo-lookup, link-rendering, identity correlation). Valid values:

| `dataTypeHint` | When to use                                                              |
|----------------|---------------------------------------------------------------------------|
| `uri`          | Columns containing URLs (logs, dashboards, source-document links)         |
| `guid`         | UUID values stored as `string` (alternative to changing the column type)  |
| `armPath`      | Azure Resource Manager resource IDs (`/subscriptions/.../resourceGroups/...`) |
| `ip`           | IPv4 or IPv6 addresses — enables `ipv4_lookup` / `geo_info_from_ip_address` query optimisation |

```json
{ "name": "SourceIPAddress", "type": "string", "dataTypeHint": "ip" }
{ "name": "TargetResourceId", "type": "string", "dataTypeHint": "armPath" }
{ "name": "EventCorrelationId", "type": "string", "dataTypeHint": "guid" }
```

`dataTypeHint` is optional and the schema's enum is closed — only those four values are
accepted.

### Column hard length limit

Column names have a hard `maxLength: 45` enforced by `table.schema.json`. There is no
"practical limit" / "soft limit" distinction — 45 is the actual ceiling. Flatten nested
paths (e.g. `actor_location.country_code` -> `ActorLocationCountryCode`) but stop
flattening before you exceed 45 characters: abbreviate or restructure (e.g.
`AssessmentCriticalConfigurationFindingDescription` is over the limit; use
`AssessmentFindingDesc` or split into multiple columns).

---

## Naming and shape rules

- **PascalCase** for column names: `EventId`, `SourceIPAddress`, `UserEmail`
- **Convert API field names**: `event_type` → `EventType`, `user.email` → `UserEmail`
- **Flatten nested objects**: `actor_location.country_code` → `ActorLocationCountryCode`
- **Pattern**: `^[A-Za-z][A-Za-z0-9_]*$` — start with a letter, alphanumeric/underscore only.
  No hyphens, spaces, or special characters.
- **No duplicate column names** within a table.
- **TimeGenerated (datetime) is REQUIRED as the first column** in every table.

Typical column count: **30–250+** per table, depending on doc completeness. If you ended up
with fewer than 30, you probably missed an event catalog page. If you produced more than 400,
double-check you haven't included envelope fields or guessed.

---

## Column-definition completion checklist

- [ ] All documentation sources fetched (spec, event catalog, human docs)
- [ ] Event catalog pages processed: union of all per-event field names extracted
- [ ] Every column traces to a verified source — no invented columns
- [ ] No catchall columns (`RawData`, `EventData`, `Payload`, `AdditionalData`, etc.)
- [ ] No pagination / envelope metadata columns (`offset`, `limit`, `total`, `hasMore`, `cursor`)
- [ ] No reserved Azure Monitor names declared (`TenantId`, `Type`, `_TimeReceived`, etc.)
- [ ] No KQL-keyword column names (`project`, `title`, `where`, `count` — renamed if encountered)
- [ ] Column count stated explicitly (sanity-check 30–250+ range)
- [ ] `TimeGenerated` included as first column with type `datetime`
- [ ] All column names use PascalCase
- [ ] Nested objects flattened to individual columns where the API documents the inner fields
- [ ] All types valid Log Analytics types from the mapping above
