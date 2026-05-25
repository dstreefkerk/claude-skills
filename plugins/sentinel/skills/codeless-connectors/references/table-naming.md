# Custom Table Naming Rules

Rules for naming `_CL` custom tables, generating `dataType` values, and validating against
Azure Monitor reserved prefixes. Apply whenever a new custom table is being created or a
new `dataType` value is being chosen.

## Naming algorithm: `{VendorName}{EndpointType}_CL`

Derive the table name automatically from the vendor and endpoint:

1. Vendor name from API docs (PascalCase, no spaces) — `Acme`, `TechCorp`, `CloudWatch`
2. Endpoint type extracted from the URL path — `/api/events` -> `Events`,
   `/api/v1/alerts` -> `Alerts`, `/audit/logs` -> `AuditLogs`
3. Concatenate and add `_CL` suffix

| Vendor       | Endpoint              | Table name             |
|--------------|-----------------------|------------------------|
| `Acme`       | `/api/events`         | `AcmeEvents_CL`        |
| `TechCorp`   | `/api/v1/alerts`      | `TechCorpAlerts_CL`    |
| `CloudWatch` | `/audit/logs`         | `CloudWatchAuditLogs_CL` |

## Format rules

- Must end with `_CL` (Custom Log suffix — Azure Monitor enforces this for custom tables)
- **4 to 63 characters** total (including `_CL`) — enforced by `table.schema.json`
  `name.minLength: 4` and `maxLength: 63`
- Pattern: `^[A-Za-z0-9-_]+$` — letters, digits, underscores, hyphens. No spaces, no
  special characters.
- Cannot start with a number
- No sensitive information (credentials, secrets, internal codenames)

## Length limits across all CCF source files

For reference, the four source-file kinds have different name-length limits enforced by
their respective schemas. Use the *shortest* applicable limit when picking a vendor stem
that will be used across files:

| File kind            | `name` minLength | `name` maxLength | Pattern                  |
|----------------------|------------------|------------------|--------------------------|
| Custom table         | 4                | 63               | `^[A-Za-z0-9-_]+$`       |
| Connector definition | 1                | **31**           | `\S` (any non-whitespace) |
| DCR                  | 1                | 64               | `^[A-Za-z0-9_.-]+$`      |
| Polling config       | — (no explicit limit) | —           | Free-form string         |
| **Column name** (inside a table) | —    | **45**           | (no schema pattern; PascalCase by convention) |

The connector definition limit of **31 characters** is the tightest — a connector for a
vendor named `Acme` is fine as `AcmeConnectorDefinition` (23 chars), but
`MultiTenantOrgConnectorDefinition` (33 chars) overflows. Choose vendor stems with this
in mind, or use abbreviated suffixes (`AcmeCD`, etc.) only when the full name doesn't
fit.

## API versions

Each file kind has a closed enum of valid `apiVersion` values (rejected if you use a
non-listed version). Latest is shown in bold:

| File kind            | Valid `apiVersion` values | Default |
|----------------------|---------------------------|---------|
| Polling config       | 2021-10-01-preview, 2022-10-01-preview, 2023-02-01-preview, 2022-12-01-preview, 2023-04-01-preview, 2024-09-01, **2025-03-01** | 2022-10-01-preview |
| Connector definition | 2022-09-01-preview, 2023-02-01, 2025-07-01-preview, **2025-09-01** | 2025-09-01 |
| DCR                  | 2021-04-01, 2021-09-01-preview, 2022-06-01-preview, 2022-06-01, 2023-03-11, 2023-04-01-preview, **2024-03-11** | 2024-03-11 |
| Custom table         | 2021-03-01-privatepreview, 2021-12-01-preview, 2022-10-01, 2023-09-01, **2025-02-01** | 2025-02-01 |

Prefer the latest GA (non-preview) version unless you need a feature only the preview
adds — the schema accepts both but preview versions can be deprecated without notice.

## Reserved prefixes — case-insensitive, REJECTED at deployment

Custom table names CANNOT start with any of these prefixes. These collide with Azure
Monitor's built-in tables, Sentinel system tables, or reserved namespaces. If the chosen
name uses a reserved prefix, pick an alternative (typically by prepending the vendor name
or qualifying the data type).

| Letter | Reserved prefixes |
|--------|-------------------|
| A | AAC, AAD, ABSBot, ACR, ACS, Adx, ADX, AEW, AGC, AGS, AKS, Alibaba, AmlCompute, AmlOnlineEndpoint, Anomalies, AOI, ARC, ASC, ASR, ATA, ATT, AWS, Azure, Azu |
| B | BaiduCloud, Barracuda, Behavior, Benchmark |
| C | CEF, Cisco, CL, Cloud, Common, Confirms, Custom, Cyberx |
| D | Device, DNS, DPS, DRA, DSM, Dynamics, Dynamics365, Dynatrace |
| E | EGN, EPM, Event, Exchange |
| F | Fabric, Failed |
| G | Google, GPC |
| H | Heartbeat, HuntingBookmark |
| I | IA, IAS, Ibiza, InsightsMetrics, Internal, ISM |
| K | KQL, Kube |
| L | LAQueryLogs, LinuxAuditLog, LogManagement |
| M | MAApplication, MADevice, MCCEvent, MDADataless, MDATP, MDCA, MDC, MDI, MDO, MicrosoftAzure, MicrosoftData |
| N | NTA |
| O | OEP, Office |
| P | Perf, PowerBI, Project, Protection |
| R | Resource |
| S | SCC, SecurityBridge, SecurityEvent, SecurityIncident, Sentinel, SentinelAudit, SentinelHealth, SharePoint, SignalR, SigninLogs, SOC, SQL, Syslog |
| T | ThreatIntelligence, Threat, TI |
| U | UCClient, UCService, Update, Usage |
| W | Watchlist, WindowsEvent |

**Notable traps:**
- `Cisco*_CL` is rejected — a Cisco-vendor connector must use a more specific prefix
  (e.g. `CiscoMerakiEvents_CL` works because the match is on the whole prefix `Cisco`
  followed by `*`; if your connector validator flags this, qualify further:
  `MerakiCiscoEvents_CL` or rename to `MerakiEvents_CL`).
- `Event*_CL`, `Custom*_CL`, `Cloud*_CL` are all rejected — these are the natural names
  many vendors would otherwise choose.
- `Sentinel*_CL`, `Security*_CL`, `Threat*_CL` are reserved for Microsoft system tables.
- `CL_CL` is reserved (the prefix `CL` itself).

If a chosen name hits a reserved prefix, the deployment fails with a generic
`InvalidTableName` or schema-validation error — the error message does NOT identify the
reserved prefix as the cause, so check this list first when troubleshooting.

## connectorDefinitionName + dataType in multi-poller connectors

When a single connector polls multiple endpoints (each producing a different table):

- **`connectorDefinitionName`** is the SAME for every polling-config array element. Use
  the pattern `{VendorName}ConnectorDefinition`. All endpoints share one definition.
- **`dataType`** is UNIQUE per array element — set it to the table name (already includes
  `_CL`).

```json
[
    {
        "name": "VendorEventsConnector",
        "properties": {
            "connectorDefinitionName": "VendorConnectorDefinition",
            "dataType": "VendorEvents_CL"
        }
    },
    {
        "name": "VendorAlertsConnector",
        "properties": {
            "connectorDefinitionName": "VendorConnectorDefinition",
            "dataType": "VendorAlerts_CL"
        }
    }
]
```

`isActive` is OPTIONAL and defaults to `true`. Set `isActive: false` only for
staging/testing polling configs that should ship in the package but not auto-poll.
