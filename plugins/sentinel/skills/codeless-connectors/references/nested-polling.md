# Nested Polling — Parent/Child Endpoint Patterns

When an API requires multi-step retrieval — first call returns a list of IDs, then each
ID requires a detail call — configure it with `stepInfo` + `stepCollectorConfigs` on the
parent endpoint's polling config. Do not create a separate top-level polling config for
the child endpoint.

## When this pattern applies

Look for documentation patterns like:
- "List then fetch details"
- "Get IDs then get records per ID"
- "For each item / per tenant / per user, call X"
- Two related endpoints where one depends on the output of the other (parent returns IDs
  in an array; child takes one ID in the URL path)

## Structure

```json
{
    "properties": {
        "connectorDefinitionName": "VendorConnectorDefinition",
        "dataType": "VendorItems_CL",
        "request": {
            "apiEndpoint": "{{BaseUrl}}/items",
            "httpMethod": "GET"
        },
        "response": {
            "eventsJsonPaths": ["$.data"]
        },
        "stepInfo": {
            "stepType": "Nested",
            "nextSteps": [
                {
                    "stepId": "fetchDetails",
                    "stepPlaceholdersParsingKql": "| extend _ItemId = id"
                }
            ]
        },
        "stepCollectorConfigs": {
            "fetchDetails": {
                "request": {
                    "apiEndpoint": "{{BaseUrl}}/items/$_ItemId$/details",
                    "httpMethod": "GET"
                },
                "response": {
                    "eventsJsonPaths": ["$"]
                }
            }
        }
    }
}
```

## Authoring rules

- `stepType` is always `"Nested"` for parent-child patterns
- `nextSteps[].stepId` must match a key in `stepCollectorConfigs`
- One poller per parent endpoint; the parent contains BOTH `stepInfo` and
  `stepCollectorConfigs`
- Children go INSIDE `stepCollectorConfigs` only — never as separate top-level array
  elements in the polling-config file
- Each child entry can have its own `request`, `response`, and `paging`
- For multiple child steps, add matching entries to both `nextSteps` and
  `stepCollectorConfigs`

## Placeholder syntax

Each child URL substitutes values extracted from the parent response.

- **Define** in `stepPlaceholdersParsingKql` with the `_` prefix:
  `| extend _ItemId = id` (extracts `id` field, names it `_ItemId`)
- **Reference** in child `apiEndpoint` with `$_` and `$` delimiters:
  `{{BaseUrl}}/items/$_ItemId$/details`
- Multiple placeholders per call are supported:
  `| extend _TenantId = tenant_id, _UserId = user.id` then
  `{{BaseUrl}}/tenants/$_TenantId$/users/$_UserId$/audit`

## Restricted KQL subset for `stepPlaceholdersParsingKql`

Use only the minimal operators needed to extract placeholder values. Do not transform or
aggregate.

| Allowed   | Use                                                                    |
|-----------|------------------------------------------------------------------------|
| `extend`  | Add a new column named after the placeholder: `\| extend _Id = id`     |
| `project` | Same effect: `\| project _Id = id`                                     |
| `where`   | Filter which parent rows trigger child calls: `\| where status == 'active' \| extend _Id = id` |

Allowed conversion functions: `tostring()`, `toint()`, `tolong()`, `todatetime()`.

`columnifexists('fieldName', defaultValue)` is allowed when a placeholder field may be
absent. The first argument MUST be a string literal.

**Forbidden** (same constraint as `transformKql`): `summarize`, `sort`, `order by`,
`take`, `limit`, `distinct`, `top`. Avoid `join`, `union`, `mv-expand`, `mv-apply` unless
absolutely necessary.

**KQL keyword collisions in field names**: if the API field is a KQL keyword (`source`,
`type`, `data`, etc.), bracket-quote it: `| extend _TypeId = tostring(['type'])`.

## Merging child data into parent records

By default, each child call produces a separate event in the destination table. To merge
the child detail back into the parent record (one row per parent + its detail), set
`shouldJoinNestedData: true` on the `stepCollectorConfigs` entry — NOT on `stepInfo`.

```json
"stepCollectorConfigs": {
    "fetchDetails": {
        "shouldJoinNestedData": true,
        "request": { "apiEndpoint": "{{BaseUrl}}/items/$_ItemId$/details" },
        "response": { "eventsJsonPaths": ["$"] }
    }
}
```

Common placement mistake: putting `shouldJoinNestedData` inside `stepInfo` instead of
inside `stepCollectorConfigs.{stepId}` — the property is silently ignored and you end up
with un-joined child events.

## Authoring checklist

- [ ] Parent endpoint configured with `request`, `response`, `paging` as usual
- [ ] `stepInfo.stepType` set to `"Nested"`
- [ ] Every `nextSteps` entry has `stepId` and `stepPlaceholdersParsingKql`
- [ ] KQL uses only `extend`/`project`/`where` (+ allowed conversion funcs) and the
      `_PlaceholderName` naming pattern
- [ ] Child URLs reference placeholders as `$_PlaceholderName$`
- [ ] Every `nextSteps[].stepId` has a matching key in `stepCollectorConfigs`
- [ ] Each child `stepCollectorConfigs` entry has its own `request` and `response`
- [ ] If child detail should merge into parent: `shouldJoinNestedData: true` is on the
      `stepCollectorConfigs` entry, not on `stepInfo`
- [ ] KQL keyword field names are bracket-quoted in placeholder extraction
