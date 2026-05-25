# CCF Source-File JSON Schemas

JSON Schemas (draft-07) for the four CCF source-file kinds: connector definition,
polling configuration, data collection rule (DCR), and Log Analytics custom table.
Use these to validate the individual building-block files **before** they're wrapped
into a deployable ARM template by `createSolutionV3.ps1`.

## Files

| Schema file                              | Validates                                                  | Bundle path in extension                          |
|------------------------------------------|------------------------------------------------------------|---------------------------------------------------|
| `connector_definition.schema.json`       | `*_ConnectorDefinition.json` (UI metadata, instructionSteps, permissions, graphQueries) | `out/schemas/connector_definition.schema.json`    |
| `rest_api_poller.schema.json`            | Polling config file(s) — array of `{name, properties: {request, response, paging, auth, dcrConfig, dataType, connectorDefinitionName}}` | `out/schemas/rest_api_poller.schema.json`         |
| `data_collection_rule.schema.json`       | DCR file (`streamDeclarations`, `destinations`, `dataFlows`, `transformKql`) | `out/schemas/data_connection_rule.schema.json` *(see filename note)* |
| `table.schema.json`                      | Custom `_CL` table resource(s) — column schemas            | `out/schemas/table.schema.json`                   |

### Filename note

Microsoft's bundle ships the DCR schema as `data_connection_rule.schema.json` —
that's a typo (the schema's own `title` is "Azure Data Collection Rule (DCR)"). It
has been renamed to `data_collection_rule.schema.json` here for clarity. The
schema content is unmodified.

## Source and license

Extracted verbatim from version 2.2.0 of the
[Microsoft Sentinel VS Code extension](https://marketplace.visualstudio.com/items?itemName=ms-security.ms-sentinel)
(`ms-security.ms-sentinel-2.2.0/out/schemas/*.json`).

Each schema's `$id` references `github.com/microsoft/sentinel-connectors/ccf-schema/...`
— **that repository does not currently exist publicly (404)**. The schemas are
distributed only inside the VS Code extension bundle.

The extension is governed by the
[Microsoft Software License Terms for the Sentinel VS Code extension](https://marketplace.visualstudio.com/items/ms-security.ms-sentinel/license),
which restrict redistribution of the extension software. These schema files
describe a publicly-documented framework (CCF / Codeless Connector Framework) and
are included here for use by validation tooling. If Microsoft objects or
publishes them at an authoritative URL, this directory will be updated to
fetch from that source instead.

## Schema validation in Python

```python
import json
from jsonschema import Draft7Validator

with open("schemas/rest_api_poller.schema.json") as f:
    schema = json.load(f)
with open("path/to/your/polling_config.json") as f:
    instance = json.load(f)

validator = Draft7Validator(schema)
errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)
for err in errors:
    print(f"{'.'.join(str(p) for p in err.absolute_path)}: {err.message}")
```

Note that schema validation alone is not sufficient — CCF has cross-file
consistency requirements (stream names in polling.dcrConfig must match
streamDeclarations keys in the DCR; polling.dataType must match a table name;
polling.connectorDefinitionName must match the connector definition file's name)
that no single-file schema can express. See the parent skill's `SKILL.md` for
the cross-file rules and the deployment checklist.

## Caveats

- The schemas validate the **source** building-block files, not the wrapped ARM
  template. For ARM-level validation (bracket escaping, dependency chains,
  top-level table existence), use the parent skill's `scripts/validate_connector.py`.
- The schemas reflect the framework state as of extension v2.2.0. Microsoft
  iterates on CCF — re-extract from a newer bundle when the extension updates,
  particularly when new connector kinds (Push, StorageAccountBlobContainer) move
  from preview to GA or new properties are added.
- Microsoft's own `validate_connector` tool inside the extension layers
  *conditional requirements* on top of the schemas (e.g. OAuth2 `authorization_code`
  requires AuthorizationCode + AuthorizationEndpoint + RedirectUri + Scope).
  Those conditionals are not expressed inside the JSON Schemas — they're enforced
  by surrounding TypeScript validation code that we did not extract.
