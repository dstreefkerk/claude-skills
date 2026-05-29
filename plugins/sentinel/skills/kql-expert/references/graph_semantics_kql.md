# KQL Graph Semantics Reference

Authoritative reference for Kusto Query Language (KQL) graph semantics in **Microsoft Sentinel** and **Azure Monitor** (also Azure Data Explorer and Microsoft Fabric Real-Time Intelligence). Graph semantics let you model tabular data as nodes and edges and traverse relationships — ideal for **lateral-movement / attack-path detection**, identity blast-radius analysis, and entity-relationship hunting.

> All behaviour below is sourced from Microsoft Learn (`learn.microsoft.com/kusto/query/...`). Always validate graph queries in an Azure Data Explorer / Kusto playground before deploying them as analytic rules, and confirm operator availability for your workspace — several operators are in **preview**.

---

## ⚠️ Breaking change: variable-length edge dot-notation is deprecated

This is the single most important thing to get right and the most common source of broken graph queries.

A **variable-length edge** (`-[e*1..5]-`) matches a *sequence* of edges, not a single edge. Historically you could reference a property of that sequence with dot-notation (`e.Prop`) and get back a dynamic array. Microsoft has **deprecated dot-notation on variable-length edges** (announced by the Azure Data Explorer team: *"Deprecation of variable length edge dot notation in graph-match"*). Use the graph functions instead.

> Caveats on specifics: the canonical `graph-match` docs example now uses `map()` (not dot-notation), and the deprecation is documented. Do **not** rely on a precise "enforcement date" or a specific semantic error code (e.g. `SEM10xx`) unless you have confirmed it against current Microsoft docs — those specifics have circulated in third-party notes without a verifiable source.

| Clause | Deprecated (variable-length edge) | Correct replacement |
|--------|-----------------------------------|---------------------|
| `project` (plain property) | `path = chain.FileName` | `path = map(chain, FileName)` |
| `project` (with a function) | `strcat(chain.FileName, "x")` | `map(chain, strcat(FileName, "x"))` |
| `project` (length/count) | `array_length(chain.FileName)` | `array_length(map(chain, FileName))` |
| `where` (must hold for **all** edges) | `chain.Action has "exploit"` | `all(chain, Action has "exploit")` |
| `where` (holds for **any** edge) | `isnotempty(chain.Action)` | `any(chain, isnotempty(Action))` |

**Rules of thumb:**
- Inside `map()` / `all()` / `any()`, reference the property **by name only** (`FileName`), **not** `chain.FileName`.
- `map(edge, expr)` returns a `dynamic` array — one element per edge in the matched path; **empty array for zero-length paths**.
- Dot-notation **still works** for **single/fixed edges and nodes** (`n.name`, a `-[e]->` edge). The deprecation is specific to **variable-length** edges.
- To operate on the **inner nodes** of a variable-length edge (the nodes between the endpoints), pass `inner_nodes(edge)` as the **first argument** to `map()` / `all()` / `any()`: `map(inner_nodes(chain), name)`. `inner_nodes()` cannot be used on its own — it is only valid in that first-argument slot.

```kql
// DEPRECATED — dot-notation on a variable-length edge
... | graph-match (start)-[chain*1..5]->(target)
      where start.name == "patient-zero"
      project hops = array_length(chain.FileName), names = chain.FileName

// CORRECT — graph functions
... | graph-match (start)-[chain*1..5]->(target)
      where start.name == "patient-zero" and all(chain, isnotempty(FileName))
      project hops = array_length(map(chain, FileName)),
              names = map(chain, FileName),
              waypoints = map(inner_nodes(chain), name)
```

---

## Operator pipeline at a glance

A graph query has three stages: **build → traverse → (optionally) convert back to a table**.

```
<tabular edges> | make-graph ...        // build a transient graph
                | graph-match / graph-shortest-paths / graph-mark-components
                | project ...           // back to tabular rows
```

| Operator | Purpose | Sentinel / Azure Monitor | Notes |
|----------|---------|--------------------------|-------|
| `make-graph` | Build a transient in-memory graph from edge (and optional node) tables | ✅ | Must be followed by a graph operator |
| `graph` (function) | Reference a **persistent** graph model/snapshot | Preview — **ADX/Fabric only** (banner omits Azure Monitor / Sentinel) | Use instead of `make-graph` for stored graphs |
| `graph-match` | Find all occurrences of a pattern | ✅ | Core traversal/pattern operator |
| `graph-shortest-paths` | Shortest path(s) between source and target node sets | ✅ (preview) | Pattern **must** include ≥1 variable-length edge |
| `graph-to-table` | Export nodes and/or edges back to tabular form | ✅ | Efficient for counting/inventory |
| `graph-mark-components` | Find & label connected components | ✅ (preview) | `kind=weak` (default) or `strong` |

> **Availability caveat:** `node_degree_in()` / `node_degree_out()` are documented as **Microsoft Fabric + Azure Data Explorer only** (the "Applies to" banner does not list Azure Monitor / Microsoft Sentinel). Don't assume they work in a Sentinel analytic rule without testing. The graph-traversal functions `map()`, `all()`, `any()`, `inner_nodes()` **do** apply to Sentinel / Azure Monitor.

---

## make-graph (build the graph)

```
Edges | make-graph SourceNodeId --> TargetNodeId [ with Nodes1 on NodeId1 [, Nodes2 on NodeId2] ]
Edges | make-graph SourceNodeId --> TargetNodeId [ with_node_id = NodeIdPropertyName ]
Edges | make-graph SourceNodeId --> TargetNodeId [ ... ] partitioned-by PartitionColumn ( GraphOperator )
```

- Each **row** of `Edges` becomes an edge; its columns become edge properties.
- Each row of a `Nodes` table becomes a node; its columns become node properties.
- Nodes that appear in `Edges` but not in `Nodes` are created with empty properties.
- Three ways to supply node info:
  1. **None** — just `source --> target`.
  2. **Explicit** — `with Nodes1 on NodeId1 [, Nodes2 on NodeId2]` (up to two node tables; same node ID in both merges properties, conflicts resolved arbitrarily).
  3. **Default identifier** — `with_node_id = name` (handy so the node ID is available in the later `where` clause).
- `partitioned-by PartitionColumn (GraphOperator)` builds a **separate graph per distinct partition value** and combines results — useful for multitenant analysis. The partition column must exist in **both** the edges table and all node tables.

**Performance — filter before you build.** `make-graph` materialises structure *and* properties in memory, so:
1. **Filter early** — keep only relevant nodes/edges/time range before `make-graph`.
2. **Project away** unused columns to cut memory.
3. **Aggregate** (e.g. `summarize arg_max(...)` for "latest state") to shrink the graph.

```kql
let nodes =
    union
        (DeviceInfo  | project nodeId = DeviceId, label = "device",  properties = pack_all(true)),
        (IdentityInfo | project nodeId = AccountUpn, label = "identity", properties = pack_all(true));
let edges =
    SigninLogs
    | where TimeGenerated > ago(7d)
    | project source = AccountUpn, destination = DeviceId, label = "signedInto";
edges
| make-graph source --> destination with nodes on nodeId
| graph-match (id)-[acts*1..4]->(dev)
    where id.label == "identity"
    project identity = id.nodeId, hops = array_length(map(acts, label))
```

---

## graph-match (pattern matching)

```
G | graph-match [cycles = all|none|unique_edges] Pattern [where Constraints] project [Name =] Expression [, ...]
```

**Pattern notation:**

| Element | Named | Anonymous |
|---------|-------|-----------|
| Node | `(n)` | `()` |
| Directed edge L→R | `-[e]->` | `-->` |
| Directed edge R→L | `<-[e]-` | `<--` |
| Any-direction edge | `-[e]-` | `--` |
| Variable-length edge | `-[e*3..5]-` | `-[*3..5]-` |

- **Constraints** (`where`) and **projections** (`project`) reference a property as `variable.property` for **nodes and single edges**. For **variable-length edges**, use `map()` / `all()` / `any()` (see the deprecation section above).
- **Multiple sequences** express non-linear patterns; comma-delimited sequences must **share a node variable**, e.g. `(a)--(n)--(b), (c)--(n)--(d)`. Only single connected-component patterns are supported.
- `cycles` controls cycle matching: `unique_edges` (default) matches cycles but no edge twice; `all` matches all; `none` excludes cycles.
- **Returns** a tabular result, one row per match. Properties of variable-length edges are returned as **dynamic arrays**.

**Attack-path example (Sentinel-style):**

```kql
let Entities = datatable(name:string, type:string)[ "Mallory","Person", "Bob","Person", "Apollo","System" ];
let Actions = datatable(source:string, destination:string, action_type:string)
[ "Mallory","Bob","attacks", "Bob","Apollo","hasPermission" ];
Actions
| make-graph source --> destination with Entities on name
| graph-match (attacker)-[attack]->(compromised)-[perm]->(system)
    where attacker.name == "Mallory" and system.type == "System"
          and attack.action_type == "attacks" and perm.action_type == "hasPermission"
    project Attacker = attacker.name, Compromised = compromised.name, System = system.name
```

---

## graph-shortest-paths (preview)

```
G | graph-shortest-paths [output = any|all] Pattern where Predicate project [Name =] Expression [, ...]
```

- Finds shortest path(s) between a set of source nodes and a set of target nodes.
- **The pattern must include at least one variable-length edge** and **cannot contain multiple sequences**.
- `output = any` (default) returns one shortest path per source/target pair; `output = all` returns all equal-minimum-length paths.
- Like `graph-match`, variable-length-edge properties come back as dynamic arrays — use `map()` to project them.

```kql
connections
| make-graph from --> to with stations on name
| graph-shortest-paths output=all (src)-[route*1..5]->(dst)
    where src.name == "South-West" and dst.name == "North"
    project src.name, stations = map(inner_nodes(route), name), lines = map(route, line), dst.name
```

---

## graph-to-table

Export a graph back to tabular form (often cheaper than `graph-match` for plain counting/inventory).

```
G | graph-to-table nodes [ with_node_id = ColumnName ]
G | graph-to-table edges [ with_source_id = ColumnName ] [ with_target_id = ColumnName ] [ as TableName ]
G | graph-to-table nodes as N [with_node_id=...], edges as E [with_source_id=...] [with_target_id=...]
```

- `with_node_id` / `with_source_id` / `with_target_id` emit the internal node **hash** (a `long`) under the given column name.
- At least one of nodes/edges must be requested.

```kql
graph('Simple') | graph-to-table edges with_source_id=SourceId with_target_id=TargetId
```

---

## graph-mark-components (preview)

```
G | graph-mark-components [kind = weak|strong] [with_component_id = ColumnName]
```

- Labels each node with a component ID (`ComponentId` by default) — a **zero-based consecutive index**.
- `weak` (default) ignores edge direction; `strong` requires connectivity in both directions.
- Component indices are arbitrary and **not stable across runs** — use them for grouping within a single query, not as persistent IDs.

---

## Graph traversal functions (use with variable-length edges)

| Function | Returns | Use in |
|----------|---------|--------|
| `map(edge, expr)` | Dynamic array of `expr` per edge | `project` |
| `map(inner_nodes(edge), expr)` | Dynamic array of `expr` per inner node | `project` |
| `all(edge, condition)` | `true` if condition holds for **every** edge (true for zero-length) | `where` |
| `any(edge, condition)` | `true` if condition holds for **≥1** edge (false for zero-length) | `where` |
| `inner_nodes(edge)` | Scopes iteration to inner nodes only (not standalone) | First arg of the above: `map(inner_nodes(e), expr)` |
| `node_degree_in([n])` / `node_degree_out([n])` | In/out degree of a node | `project` / `where` — **ADX/Fabric only (verify in Sentinel)** |

Inside these functions reference properties **by name only** (no `edge.`/`node.` prefix). When `node_degree_in`/`node_degree_out` are used inside `all`/`any`/`map` with `inner_nodes()`, call them with **no argument**.

---

## Transient vs persistent graphs

- **Transient** (`make-graph`): built in-memory per query. Best for ad-hoc hunting and small/medium data. This is what almost all Sentinel/Azure Monitor use cases rely on.
- **Persistent** (`graph()` function + graph models/snapshots): stored, versioned, reusable. **Preview**, and the `graph()` function's "Applies to" banner lists **Azure Data Explorer / Fabric only** (not Azure Monitor / Sentinel) — don't assume persistent graphs are available in a Sentinel workspace without checking. Per the *Persistent graphs overview (preview)* page, documented limits are: max **5,000** snapshots per database (**500** on a free virtual cluster) and a snapshot creation time limit of **1 hour**.

```kql
graph("MyGraphModel")               // latest snapshot
| graph-match (n)-[e]->(m) project n, e, m

graph("MyGraphModel", "Snapshot1")  // specific snapshot
| graph-match (n)-[e]->(m) project n, e, m
```

---

## Common mistakes

| Mistake | Fix |
|---------|-----|
| `chain.Prop` on a variable-length edge | `map(chain, Prop)` (project) or `all/any(chain, ...)` (where) |
| Prefixing the property inside `map`/`all`/`any` (`map(chain, chain.Prop)`) | Reference by name only: `map(chain, Prop)` |
| `graph-shortest-paths` with a fixed-length-only pattern | Include a variable-length edge (`-[e*1..n]-`) |
| Building the graph on unfiltered tables | Filter/project/aggregate **before** `make-graph` |
| Assuming `node_degree_in/out` work in Sentinel | Documented for ADX/Fabric only — test first |
| Treating `graph-mark-components` IDs as stable | Indices are arbitrary per run |
| Deploying an untested graph rule | Validate in an ADX/Kusto playground first; analytic-rule semantic errors can fire silently |

---

## Sources (Microsoft Learn)

- Graph operators overview — `learn.microsoft.com/kusto/query/graph-operators`
- make-graph — `learn.microsoft.com/kusto/query/make-graph-operator`
- graph-match — `learn.microsoft.com/kusto/query/graph-match-operator`
- graph-shortest-paths — `learn.microsoft.com/kusto/query/graph-shortest-paths-operator`
- graph-to-table — `learn.microsoft.com/kusto/query/graph-to-table-operator`
- graph-mark-components — `learn.microsoft.com/kusto/query/graph-mark-components-operator`
- map / all / any / inner_nodes — `learn.microsoft.com/kusto/query/{map,all,any,inner-nodes}-graph-function`
- node_degree_in / node_degree_out — `learn.microsoft.com/kusto/query/{node-degree-in,node-degree-out}`
- Best practices for graph semantics — `learn.microsoft.com/kusto/query/graph-best-practices`
- Persistent graphs overview (preview), incl. snapshot limits — `learn.microsoft.com/kusto/management/graph/graph-persistent-overview`
- graph() function — `learn.microsoft.com/kusto/query/graph-function`
- Deprecation of variable length edge dot notation in graph-match — Azure Data Explorer blog, Microsoft Community Hub
