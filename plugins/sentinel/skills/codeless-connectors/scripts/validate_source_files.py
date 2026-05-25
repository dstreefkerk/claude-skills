#!/usr/bin/env python3
"""
CCF Source-File Validator

Validates Microsoft Sentinel Codeless Connector Framework (CCF) source files
BEFORE they're wrapped into a deployable ARM template by createSolutionV3.ps1.

Complementary to validate_connector.py (which validates the wrapped ARM template
post-packaging). Run this during authoring to catch:

  1. JSON Schema violations (structural correctness against schemas/*.schema.json)
  2. Conditional requirements schemas can't express (OAuth2 auth_code extra fields,
     {{apiKey}} literal-placeholder rule, etc.)
  3. Cross-file consistency (stream names match, dataType matches table name,
     connectorDefinitionName matches, instructionSteps Textbox names match
     {{placeholders}} in polling)
  4. Domain rules (reserved table prefixes, catchall column names, _CL suffix,
     ConnectionToggleButton-last UX trap, etc.)

Usage:
    python validate_source_files.py polling.json [dcr.json] [table.json] [connector_def.json]
    python validate_source_files.py --folder path/to/connector_folder
    python validate_source_files.py --verbose polling.json
    python validate_source_files.py --strict polling.json    # warnings -> failures

Requires: jsonschema (pip install jsonschema)

Exit codes:
    0 = all checks pass (warnings allowed unless --strict)
    1 = one or more failures
    2 = setup error (missing dependency, schema not found, bad CLI args)
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

try:
    from jsonschema import Draft7Validator
    from jsonschema.exceptions import best_match
except ImportError:
    sys.stderr.write(
        "ERROR: 'jsonschema' package is required.\n"
        "Install with: pip install jsonschema\n"
    )
    sys.exit(2)


# ---------------------------------------------------------------------------
# Paths and schemas
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_DIR = SCRIPT_DIR.parent / "schemas"

SCHEMA_FILES = {
    "polling": "rest_api_poller.schema.json",
    "dcr": "data_collection_rule.schema.json",
    "table": "table.schema.json",
    "connector_definition": "connector_definition.schema.json",
    # 'push' shares no bundled schema — handled with domain checks only
}

KIND_LABELS = {
    "polling": "Polling Config",
    "push": "Push Connector",
    "dcr": "DCR",
    "table": "Table",
    "connector_definition": "Connector Definition",
}


# ---------------------------------------------------------------------------
# Domain constants (from references/table-naming.md, field-discovery.md, etc.)
# ---------------------------------------------------------------------------

OAUTH2_AUTHCODE_REDIRECT_URI = (
    "https://portal.azure.com/TokenAuthorize/ExtensionName/"
    "Microsoft_Azure_Security_Insights"
)
OAUTH2_AUTHCODE_REQUIRED_EXTRA = [
    "AuthorizationCode",
    "AuthorizationEndpoint",
    "RedirectUri",
    "Scope",
]

# Reserved Azure Monitor column names (case-insensitive)
RESERVED_COLUMN_NAMES = {
    name.lower()
    for name in [
        "TenantId", "Type", "_TimeReceived", "_ItemId", "_ResourceId",
        "_SubscriptionId", "_IsBillable", "_BilledSize", "SourceSystem",
        "MG", "ManagementGroupName", "Computer", "RawData",
    ]
}

# Catchall column names — bundle-everything anti-pattern (case-insensitive)
FORBIDDEN_CATCHALL_NAMES = {
    name.lower()
    for name in [
        "RawEventData", "EventRawData", "RawData", "EventData", "FullEvent",
        "AllFields", "Payload", "Data", "AdditionalData", "ExtraFields",
        "Properties", "Details", "Body", "Content", "RawJson",
    ]
}

# Pagination/envelope metadata — not event data (case-insensitive)
FORBIDDEN_ENVELOPE_NAMES = {
    name.lower()
    for name in [
        "offset", "limit", "total", "hasMore", "count", "page", "nextPage",
        "cursor", "continuation", "pageCount",
    ]
}

# KQL keywords — warn-only because rename is the fix (case-insensitive)
KQL_KEYWORD_COLUMN_NAMES = {
    name.lower()
    for name in [
        "project", "title", "where", "extend", "join", "let", "order",
        "search", "union", "count", "filter", "summarize", "sort", "parse",
        "limit", "top", "take", "set", "print", "render", "invoke", "find",
        "fork", "scan", "reduce", "sample", "distinct", "evaluate", "lookup",
        "materialize", "serialize", "partition", "consume", "between", "in",
        "of", "to", "not", "and", "or", "has", "contains", "startswith",
    ]
}

# Reserved table-name prefixes (case-insensitive)
RESERVED_TABLE_PREFIXES = [
    p.lower() for p in [
        "AAC", "AAD", "ABSBot", "ACR", "ACS", "Adx", "ADX", "AEW", "AGC",
        "AGS", "AKS", "Alibaba", "AmlCompute", "AmlOnlineEndpoint", "Anomalies",
        "AOI", "ARC", "ASC", "ASR", "ATA", "ATT", "AWS", "Azure", "Azu",
        "BaiduCloud", "Barracuda", "Behavior", "Benchmark",
        "CEF", "Cisco", "CL", "Cloud", "Common", "Confirms", "Custom", "Cyberx",
        "Device", "DNS", "DPS", "DRA", "DSM", "Dynamics", "Dynamics365", "Dynatrace",
        "EGN", "EPM", "Event", "Exchange",
        "Fabric", "Failed",
        "Google", "GPC",
        "Heartbeat", "HuntingBookmark",
        "IA", "IAS", "Ibiza", "InsightsMetrics", "Internal", "ISM",
        "KQL", "Kube",
        "LAQueryLogs", "LinuxAuditLog", "LogManagement",
        "MAApplication", "MADevice", "MCCEvent", "MDADataless", "MDATP",
        "MDCA", "MDC", "MDI", "MDO", "MicrosoftAzure", "MicrosoftData",
        "NTA",
        "OEP", "Office",
        "Perf", "PowerBI", "Project", "Protection",
        "Resource",
        "SCC", "SecurityBridge", "SecurityEvent", "SecurityIncident",
        "Sentinel", "SentinelAudit", "SentinelHealth", "SharePoint", "SignalR",
        "SigninLogs", "SOC", "SQL", "Syslog",
        "ThreatIntelligence", "Threat", "TI",
        "UCClient", "UCService", "Update", "Usage",
        "Watchlist", "WindowsEvent",
    ]
]


# ---------------------------------------------------------------------------
# Result model + reporting
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str = ""
    warning: bool = False
    file_label: str = ""
    property_path: str = ""

    def __str__(self) -> str:
        status = "WARN" if self.warning else ("PASS" if self.passed else "FAIL")
        label = f"[{self.file_label}] " if self.file_label else ""
        line = f"  {status}  {label}{self.name}"
        if self.message:
            line += f"\n        {self.message}"
        if self.property_path:
            line += f"\n        Path: {self.property_path}"
        return line


# ---------------------------------------------------------------------------
# Loading and classification
# ---------------------------------------------------------------------------

def load_schemas() -> dict[str, dict]:
    schemas = {}
    missing = []
    for kind, fname in SCHEMA_FILES.items():
        path = SCHEMA_DIR / fname
        if not path.exists():
            missing.append(str(path))
            continue
        with path.open("r", encoding="utf-8") as f:
            schemas[kind] = json.load(f)
    if missing:
        sys.stderr.write(
            "ERROR: required schema files not found:\n  "
            + "\n  ".join(missing)
            + "\n"
        )
        sys.exit(2)
    return schemas


def classify_file(content: Union[dict, list]) -> Optional[str]:
    """Identify what kind of CCF file this is by inspecting type/kind fields."""
    # If it's an array, classify by the first element
    sample = content[0] if isinstance(content, list) and content else content
    if not isinstance(sample, dict):
        return None
    rtype = sample.get("type", "")
    rkind = sample.get("kind", "")
    if rtype == "Microsoft.SecurityInsights/dataConnectors" and rkind == "RestApiPoller":
        return "polling"
    if rtype == "Microsoft.SecurityInsights/dataConnectors" and rkind == "Push":
        return "push"
    if rtype == "Microsoft.SecurityInsights/dataConnectorDefinitions":
        return "connector_definition"
    if rtype == "Microsoft.Insights/dataCollectionRules":
        return "dcr"
    if rtype == "Microsoft.OperationalInsights/workspaces/tables":
        return "table"
    return None


def load_json_file(path: Path) -> tuple[Optional[Union[dict, list]], Optional[str]]:
    """Returns (content, error_message). error_message is None on success."""
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), None
    except json.JSONDecodeError as e:
        return None, f"JSON syntax error at line {e.lineno} col {e.colno}: {e.msg}"
    except OSError as e:
        return None, f"Could not read file: {e}"


# ---------------------------------------------------------------------------
# Schema validation runner
# ---------------------------------------------------------------------------

def _explain_oneOf(err) -> str:
    """For a oneOf failure, identify the branch whose discriminator field matched
    and report ITS specific errors (typically a missing required property), rather
    than the misleading generic 'matches none' message or the wrong-branch
    'Textbox was expected' message from best_match."""
    if err.validator != "oneOf" or not err.context:
        return err.message

    # Identify the discriminator field on the instance
    discriminator_field = None
    if isinstance(err.instance, dict):
        for field in ("type", "pagingType", "kind"):
            if field in err.instance:
                discriminator_field = field
                break

    prefix = ""
    if discriminator_field:
        prefix = f"For {discriminator_field}={err.instance[discriminator_field]!r}: "

    if discriminator_field:
        # Group context errors by oneOf branch index. jsonschema sub-errors
        # have schema_path[0] = the branch index (integer) when they're under
        # a oneOf validation. Errors not on the discriminator field signal a
        # branch where the discriminator matched but other validation failed.
        by_branch: dict = {}
        for sub in err.context:
            path_parts = list(sub.schema_path)
            if not path_parts or not isinstance(path_parts[0], int):
                continue
            branch_idx = path_parts[0]
            by_branch.setdefault(branch_idx, []).append(sub)

        # Matching branch = one with NO error on the discriminator field
        matching = []
        for branch_idx, branch_errors in by_branch.items():
            has_discriminator_failure = any(
                list(e.absolute_path)
                and list(e.absolute_path)[-1] == discriminator_field
                and e.validator == "const"
                for e in branch_errors
            )
            if not has_discriminator_failure:
                matching.append((branch_idx, branch_errors))

        if len(matching) >= 1:
            # If multiple branches match (unusual), pick the first
            _, errors = matching[0]
            msgs = []
            for e in errors[:3]:
                p = ".".join(str(p) for p in e.absolute_path) or "(this object)"
                msgs.append(f"{e.message} (at {p})")
            return prefix + "; ".join(msgs)

    # Fallback: best_match
    bm = best_match(err.context)
    if bm is not None:
        sub_path_parts = list(bm.absolute_path)
        sub_path = ".".join(str(p) for p in sub_path_parts) if sub_path_parts else "(this object)"
        return f"{prefix}{bm.message} (at {sub_path})"
    return err.message


def run_schema_validation(
    content: Union[dict, list],
    schema: dict,
    file_label: str,
) -> list[CheckResult]:
    """Validate content against schema. For arrays, validate each element and
    DEDUPLICATE identical errors that recur across elements (otherwise a single
    defect repeated in N array elements produces N copies of the same message)."""
    results = []
    validator = Draft7Validator(schema)

    items = content if isinstance(content, list) else [content]
    multi = isinstance(content, list) and len(items) > 1

    if not multi:
        # Single object: report errors directly.
        errors = sorted(validator.iter_errors(items[0]), key=lambda e: list(e.path))
        if not errors:
            results.append(CheckResult(
                "JSON Schema valid", True, file_label=file_label,
            ))
            return results
        for err in errors:
            path = ".".join(str(p) for p in err.absolute_path) or "(root)"
            msg = _explain_oneOf(err) if err.validator == "oneOf" else err.message
            results.append(CheckResult(
                "JSON Schema valid", False, msg,
                file_label=file_label, property_path=path,
            ))
        return results

    # Array: dedupe identical errors across elements. The "identity" of an
    # error is (relative-path-with-element-index-stripped, message). Track
    # which array element indices each unique error appeared in.
    aggregated: dict[tuple, dict] = {}
    clean_indices = []
    for idx, item in enumerate(items):
        errors = sorted(validator.iter_errors(item), key=lambda e: list(e.path))
        if not errors:
            clean_indices.append(idx)
            continue
        for err in errors:
            # Strip the leading element index from the absolute path so the
            # same error in different elements normalizes to the same key.
            path_parts = list(err.absolute_path)
            rel_path = ".".join(str(p) for p in path_parts) or "(root)"
            msg = _explain_oneOf(err) if err.validator == "oneOf" else err.message
            key = (rel_path, msg)
            agg = aggregated.setdefault(key, {
                "indices": [], "path": rel_path, "message": msg,
            })
            agg["indices"].append(idx)

    if clean_indices:
        if len(clean_indices) == len(items):
            results.append(CheckResult(
                "JSON Schema valid",
                True,
                f"All {len(items)} array elements valid",
                file_label=file_label,
            ))
        else:
            results.append(CheckResult(
                "JSON Schema valid",
                True,
                f"{len(clean_indices)} of {len(items)} array elements valid: {clean_indices}",
                file_label=file_label,
            ))

    for agg in aggregated.values():
        indices = agg["indices"]
        if len(indices) == len(items):
            suffix = f" (all {len(items)} array elements)"
        elif len(indices) > 1:
            suffix = f" (array elements {indices})"
        else:
            suffix = f" (array element {indices[0]})"
        results.append(CheckResult(
            "JSON Schema valid",
            False,
            agg["message"] + suffix,
            file_label=file_label,
            property_path=agg["path"],
        ))
    return results


# ---------------------------------------------------------------------------
# Per-kind domain checks (the things schemas can't express)
# ---------------------------------------------------------------------------

def _polling_elements(content: Union[dict, list]) -> list[dict]:
    return content if isinstance(content, list) else [content]


def _first_dict(content: Union[dict, list, None]) -> Optional[dict]:
    """Return the first dict from content (which may be a single dict, a list
    of dicts, or None). DCR and connector_definition files are normally single
    objects but some production connectors wrap them in arrays — this lets
    domain and cross-file checks work in both cases."""
    if isinstance(content, dict):
        return content
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                return item
    return None


def _dict_elements(content: Union[dict, list, None]) -> list[dict]:
    """Return all dict elements from content. For DCR/connector_definition
    files wrapped as arrays, we want to run domain checks on every element."""
    if isinstance(content, dict):
        return [content]
    if isinstance(content, list):
        return [item for item in content if isinstance(item, dict)]
    return []


def check_polling_domain(content: Union[dict, list], file_label: str) -> list[CheckResult]:
    results = []
    for idx, element in enumerate(_polling_elements(content)):
        suffix = f" [{idx}]" if isinstance(content, list) and len(content) > 1 else ""
        props = element.get("properties", {}) or {}
        auth = props.get("auth", {}) or {}
        auth_type = auth.get("type", "")

        # 1. APIKey: ApiKey must be the literal "{{apiKey}}" CCF placeholder
        if auth_type == "APIKey":
            api_key_value = auth.get("ApiKey", "")
            if api_key_value and api_key_value != "{{apiKey}}":
                # Allow ARM expression form too (for already-packaged source)
                if not re.match(r"^\[\[?parameters\(", api_key_value):
                    results.append(CheckResult(
                        f"APIKey ApiKey placeholder is fixed literal{suffix}",
                        False,
                        f"auth.ApiKey value is {api_key_value!r}; CCF requires the "
                        f"literal '{{{{apiKey}}}}' for source files (or an ARM "
                        f"parameter expression for packaged templates).",
                        file_label=file_label,
                        property_path=f"properties.auth.ApiKey",
                    ))
                else:
                    results.append(CheckResult(
                        f"APIKey ApiKey placeholder is fixed literal{suffix}",
                        True,
                        f"ARM expression form ({api_key_value[:40]}...)",
                        file_label=file_label,
                    ))
            elif api_key_value == "{{apiKey}}":
                results.append(CheckResult(
                    f"APIKey ApiKey placeholder is fixed literal{suffix}",
                    True,
                    file_label=file_label,
                ))

        # 2. OAuth2 + authorization_code: 4 extra fields required
        if auth_type == "OAuth2" and auth.get("GrantType") == "authorization_code":
            missing = [k for k in OAUTH2_AUTHCODE_REQUIRED_EXTRA if k not in auth]
            if missing:
                results.append(CheckResult(
                    f"OAuth2 authorization_code has required fields{suffix}",
                    False,
                    f"Missing: {', '.join(missing)}",
                    file_label=file_label,
                    property_path="properties.auth",
                ))
            else:
                results.append(CheckResult(
                    f"OAuth2 authorization_code has required fields{suffix}",
                    True,
                    file_label=file_label,
                ))
            # RedirectUri must be the exact portal URL
            redirect = auth.get("RedirectUri", "")
            if redirect and redirect != OAUTH2_AUTHCODE_REDIRECT_URI:
                # Allow ARM expression
                if not re.match(r"^\[\[?", redirect):
                    results.append(CheckResult(
                        f"OAuth2 RedirectUri is the Sentinel portal URL{suffix}",
                        False,
                        f"Got {redirect!r}; must be {OAUTH2_AUTHCODE_REDIRECT_URI!r}",
                        file_label=file_label,
                        property_path="properties.auth.RedirectUri",
                    ))

        # 3. dataType / dcrConfig.streamName presence (cross-file uses these)
        data_type = props.get("dataType", "")
        if not data_type:
            results.append(CheckResult(
                f"dataType is set{suffix}",
                False,
                "properties.dataType is required for cross-file consistency",
                file_label=file_label,
                property_path="properties.dataType",
            ))

        dcr_cfg = props.get("dcrConfig", {}) or {}
        stream_name = dcr_cfg.get("streamName", "")
        if stream_name and not (stream_name.startswith("Custom-") or stream_name.startswith("Microsoft-")):
            results.append(CheckResult(
                f"dcrConfig.streamName has Custom- or Microsoft- prefix{suffix}",
                False,
                f"streamName {stream_name!r} must start with 'Custom-' (third-party) "
                f"or 'Microsoft-' (Microsoft tables)",
                file_label=file_label,
                property_path="properties.dcrConfig.streamName",
            ))

    return results


def check_push_domain(content: Union[dict, list], file_label: str) -> list[CheckResult]:
    """Push connectors have a minimal polling-config shape (no auth/request/response).
    Check what we can: name + kind + dcrConfig + connectorDefinitionName."""
    results = []
    # Push is normally a single object, not an array, but handle both
    elements = content if isinstance(content, list) else [content]
    for idx, element in enumerate(elements):
        suffix = f" [{idx}]" if len(elements) > 1 else ""
        if not isinstance(element, dict):
            continue
        if element.get("kind") != "Push":
            continue
        props = element.get("properties", {}) or {}

        # 1. connectorDefinitionName required
        if not props.get("connectorDefinitionName"):
            results.append(CheckResult(
                f"Push connector has connectorDefinitionName{suffix}",
                False,
                "Push connectors must reference a connector definition",
                file_label=file_label,
                property_path="properties.connectorDefinitionName",
            ))

        # 2. dcrConfig.streamName required and Custom- prefixed
        dcr_cfg = props.get("dcrConfig", {}) or {}
        stream_name = dcr_cfg.get("streamName", "")
        if not stream_name:
            results.append(CheckResult(
                f"Push connector has dcrConfig.streamName{suffix}",
                False,
                "Push connectors must declare the inbound DCR stream name",
                file_label=file_label,
                property_path="properties.dcrConfig.streamName",
            ))
        elif not (stream_name.startswith("Custom-") or stream_name.startswith("Microsoft-")):
            results.append(CheckResult(
                f"Push dcrConfig.streamName has Custom- or Microsoft- prefix{suffix}",
                False,
                f"streamName {stream_name!r} must start with 'Custom-' or 'Microsoft-'",
                file_label=file_label,
                property_path="properties.dcrConfig.streamName",
            ))

        # 3. auth.type should be Push
        auth = props.get("auth", {}) or {}
        if auth and auth.get("type") not in (None, "Push"):
            results.append(CheckResult(
                f"Push auth.type is 'Push'{suffix}",
                True,
                f"auth.type is {auth.get('type')!r}; expected 'Push' (or absent) for Push connectors",
                warning=True,
                file_label=file_label,
                property_path="properties.auth.type",
            ))

    return results


def check_table_domain(content: Union[dict, list], file_label: str) -> list[CheckResult]:
    results = []
    tables = content if isinstance(content, list) else [content]

    for idx, table in enumerate(tables):
        suffix = f" [{idx}]" if len(tables) > 1 else ""
        name = table.get("name", "")
        props = table.get("properties", {}) or {}
        schema_obj = props.get("schema", {}) or {}
        columns = schema_obj.get("columns", []) or []

        # 1. _CL suffix required
        if name and not name.endswith("_CL"):
            results.append(CheckResult(
                f"Table name ends with _CL{suffix}",
                False,
                f"Got {name!r}; custom tables must end with '_CL'",
                file_label=file_label,
                property_path="name",
            ))
        elif name:
            results.append(CheckResult(
                f"Table name ends with _CL{suffix}",
                True,
                file_label=file_label,
            ))

        # 2. Reserved prefix (warn — interpretation varies)
        if name:
            lower_name = name.lower()
            matched = next(
                (p for p in RESERVED_TABLE_PREFIXES if lower_name.startswith(p)),
                None,
            )
            if matched:
                results.append(CheckResult(
                    f"Table name does not start with a reserved prefix{suffix}",
                    True,  # passes overall (warning only)
                    f"Table name {name!r} starts with reserved prefix {matched!r}. "
                    f"Azure may reject this at deployment. Consider qualifying with a "
                    f"vendor stem or renaming.",
                    warning=True,
                    file_label=file_label,
                    property_path="name",
                ))

        # 3. TimeGenerated as first column
        if columns:
            first = columns[0] if columns else {}
            if first.get("name") != "TimeGenerated":
                # Is it present at all?
                has_tg = any(c.get("name") == "TimeGenerated" for c in columns)
                if not has_tg:
                    results.append(CheckResult(
                        f"TimeGenerated column is present{suffix}",
                        False,
                        "TimeGenerated (datetime) is required as the first column",
                        file_label=file_label,
                        property_path="properties.schema.columns",
                    ))
                else:
                    results.append(CheckResult(
                        f"TimeGenerated is the first column{suffix}",
                        True,
                        "Present but not first; convention is first column",
                        warning=True,
                        file_label=file_label,
                    ))
            else:
                if first.get("type") != "datetime":
                    results.append(CheckResult(
                        f"TimeGenerated has type datetime{suffix}",
                        False,
                        f"TimeGenerated type is {first.get('type')!r}, must be 'datetime'",
                        file_label=file_label,
                        property_path="properties.schema.columns[0].type",
                    ))

        # 4. Forbidden column names
        for col in columns:
            col_name = col.get("name", "")
            if not col_name:
                continue
            lower = col_name.lower()
            if lower in RESERVED_COLUMN_NAMES:
                results.append(CheckResult(
                    f"No reserved Azure Monitor column names{suffix}",
                    False,
                    f"Column {col_name!r} is reserved by Azure Monitor and will be "
                    f"auto-injected; declaring it causes deployment errors",
                    file_label=file_label,
                    property_path=f"properties.schema.columns[name={col_name}]",
                ))
            elif lower in FORBIDDEN_CATCHALL_NAMES:
                results.append(CheckResult(
                    f"No catchall columns{suffix}",
                    False,
                    f"Column {col_name!r} is a catchall name. Replace with the "
                    f"specific documented fields it would contain.",
                    file_label=file_label,
                    property_path=f"properties.schema.columns[name={col_name}]",
                ))
            elif lower in FORBIDDEN_ENVELOPE_NAMES:
                results.append(CheckResult(
                    f"No pagination/envelope columns{suffix}",
                    False,
                    f"Column {col_name!r} looks like response-envelope metadata, "
                    f"not event data. Only declare fields from inside the event objects.",
                    file_label=file_label,
                    property_path=f"properties.schema.columns[name={col_name}]",
                ))
            elif lower in KQL_KEYWORD_COLUMN_NAMES:
                results.append(CheckResult(
                    f"Column name avoids KQL keyword collisions{suffix}",
                    True,
                    f"Column {col_name!r} collides with a KQL operator; users will "
                    f"need bracket notation in every query. Suggest renaming "
                    f"(e.g. {col_name!r} -> '{col_name}Name' or '{col_name}Value').",
                    warning=True,
                    file_label=file_label,
                    property_path=f"properties.schema.columns[name={col_name}]",
                ))

    return results


def check_dcr_domain(content: dict, file_label: str) -> list[CheckResult]:
    results = []
    props = content.get("properties", {}) or {}
    stream_decls = props.get("streamDeclarations", {}) or {}
    data_flows = props.get("dataFlows", []) or []

    # 1. Each dataFlows[].streams must reference a declared stream
    for i, flow in enumerate(data_flows):
        for stream in flow.get("streams", []):
            if stream not in stream_decls:
                results.append(CheckResult(
                    "dataFlows reference declared streams",
                    False,
                    f"dataFlows[{i}].streams references {stream!r} but it's not in "
                    f"streamDeclarations (declared: {sorted(stream_decls.keys())})",
                    file_label=file_label,
                    property_path=f"properties.dataFlows[{i}].streams",
                ))

    # 2. streamDeclarations keys must start with Custom-
    for stream_name in stream_decls:
        if not stream_name.startswith("Custom-"):
            results.append(CheckResult(
                "streamDeclarations keys use Custom- prefix",
                False,
                f"Stream {stream_name!r} must start with 'Custom-' (even when "
                f"targeting an ASIM table — the prefix is for the input stream)",
                file_label=file_label,
                property_path=f"properties.streamDeclarations.{stream_name}",
            ))

    # 3. outputStream prefix vs destination
    for i, flow in enumerate(data_flows):
        out = flow.get("outputStream", "")
        if not out:
            continue
        if not (out.startswith("Custom-") or out.startswith("Microsoft-")):
            results.append(CheckResult(
                "dataFlows outputStream uses Custom- or Microsoft- prefix",
                False,
                f"outputStream {out!r} must start with 'Custom-' (custom table) or "
                f"'Microsoft-' (ASIM/standard table)",
                file_label=file_label,
                property_path=f"properties.dataFlows[{i}].outputStream",
            ))

    return results


def _walk_instruction_steps(steps: list) -> list[tuple[str, dict]]:
    """Yields (path, instruction) for every instruction in nested steps."""
    out = []
    for i, step in enumerate(steps):
        for j, instr in enumerate(step.get("instructions", [])):
            base = f"instructionSteps[{i}].instructions[{j}]"
            out.append((base, instr))
            # ContextPane and InstructionStepsGroup nest further
            params = instr.get("parameters", {}) or {}
            for nested in params.get("instructionSteps", []) or []:
                for k, sub in enumerate(nested.get("instructions", [])):
                    out.append((f"{base}.parameters.instructionSteps...instructions[{k}]", sub))
    return out


def check_connector_definition_domain(content: dict, file_label: str) -> list[CheckResult]:
    results = []
    props = content.get("properties", {}) or {}
    ui = props.get("connectorUiConfig", {}) or {}
    steps = ui.get("instructionSteps", []) or []

    # 1. ConnectionToggleButton must be the last element in its instructions array
    for i, step in enumerate(steps):
        instrs = step.get("instructions", []) or []
        toggle_indices = [
            j for j, instr in enumerate(instrs)
            if instr.get("type") == "ConnectionToggleButton"
        ]
        if toggle_indices:
            last_idx = len(instrs) - 1
            misplaced = [j for j in toggle_indices if j != last_idx]
            if misplaced:
                results.append(CheckResult(
                    "ConnectionToggleButton is last in its instructions array",
                    False,
                    f"instructionSteps[{i}].instructions has ConnectionToggleButton "
                    f"at position(s) {misplaced} but it must be the last element "
                    f"(position {last_idx})",
                    file_label=file_label,
                    property_path=f"properties.connectorUiConfig.instructionSteps[{i}].instructions",
                ))

    # 2. Every credential Textbox should have validations.required:true
    #    (We can't tell which Textboxes are 'credential' without auth-type context,
    #    so we warn for any Textbox missing validations.required:true that's a
    #    password-type input — those are always required.)
    for path, instr in _walk_instruction_steps(steps):
        if instr.get("type") != "Textbox":
            continue
        params = instr.get("parameters", {}) or {}
        is_password = params.get("type") == "password"
        validations = params.get("validations", {}) or {}
        is_required = validations.get("required") is True
        if is_password and not is_required:
            name = params.get("name", "?")
            results.append(CheckResult(
                "Password Textboxes have validations.required:true",
                True,
                f"{path} (name={name!r}) is type=password but missing "
                f"validations.required:true; field will appear optional in the UI.",
                warning=True,
                file_label=file_label,
                property_path=path,
            ))

    return results


# ---------------------------------------------------------------------------
# Cross-file consistency
# ---------------------------------------------------------------------------

PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")
# Matches ARM-style references that authors use to wrap source files for direct
# ARM deployment: [parameters('name')] or [[parameters('name')]
ARM_PARAM_RE = re.compile(r"\[\[?parameters\('(\w+)'\)")


def _collect_placeholders(value) -> set[str]:
    """Recursively scan a JSON-like value for {{name}} placeholders AND
    [[parameters('name')] ARM references. Both bind to UI Textbox names."""
    found = set()
    if isinstance(value, str):
        found.update(PLACEHOLDER_RE.findall(value))
        found.update(ARM_PARAM_RE.findall(value))
    elif isinstance(value, dict):
        for v in value.values():
            found |= _collect_placeholders(v)
    elif isinstance(value, list):
        for v in value:
            found |= _collect_placeholders(v)
    return found


def _has_arm_param_references(value) -> bool:
    """True if the value contains any ARM-style [[parameters('X')] references.
    Used to decide whether Textbox-binding cross-checks make sense — when a file
    binds via ARM, the {{}}<->Textbox-name relationship is bypassed."""
    if isinstance(value, str):
        return bool(ARM_PARAM_RE.search(value))
    if isinstance(value, dict):
        return any(_has_arm_param_references(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_arm_param_references(v) for v in value)
    return False


def _collect_textbox_names(steps: list) -> set[str]:
    names = set()
    for _, instr in _walk_instruction_steps(steps):
        params = instr.get("parameters", {}) or {}
        if instr.get("type") == "Textbox":
            n = params.get("name")
            if n:
                names.add(n)
        elif instr.get("type") == "OAuthForm":
            # OAuthForm provides clientId / clientSecret implicitly
            names.update(["clientId", "clientSecret"])
    return names


# Placeholders satisfied by other sources (not Textbox inputs). These names
# appear in polling/push source files but are filled at deploy/runtime by ARM,
# Sentinel, or the OAuth flow -- not by user input in a Textbox.
IMPLICIT_PLACEHOLDERS = {
    # ARM workspace context
    "location",
    "workspace-location",
    "workspace-id",
    "workspaceName",
    "subscriptionId",
    "tenantId",
    "resourceGroupName",
    # Runtime CCF parameter objects (referenced as
    # `[parameters('X').sub-field]` -- X itself is auto-injected, never a Textbox)
    "auth",
    "dcrConfig",
    "dataCollectionEndpoint",
    "dataCollectionRuleImmutableId",
    "connectorVersion",
    "solutionVersion",
    # OAuth2 authorization-code injected during the OAuth flow
    "code",
}


def cross_file_checks(by_kind: dict[str, list[tuple[Path, Union[dict, list]]]]) -> list[CheckResult]:
    """Run cross-file consistency checks across whichever files were provided."""
    results = []

    # Push connectors play the same role as a polling config for cross-file
    # consistency (connectorDefinitionName, dcrConfig.streamName, dataType if any)
    polling_entry = (
        by_kind["polling"][0] if by_kind["polling"]
        else by_kind["push"][0] if by_kind["push"]
        else None
    )
    dcr_entry = by_kind["dcr"][0] if by_kind["dcr"] else None
    cd_entry = by_kind["connector_definition"][0] if by_kind["connector_definition"] else None
    table_entries = by_kind["table"]

    polling_label = polling_entry[0].name if polling_entry else None
    dcr_label = dcr_entry[0].name if dcr_entry else None

    polling_elements = _polling_elements(polling_entry[1]) if polling_entry else []

    # 1. polling.dcrConfig.streamName must match dcr.streamDeclarations keys.
    #    DCR may be a single object OR an array of DCR resources; union the
    #    streamDeclarations across all elements so multi-DCR connectors validate.
    if polling_entry and dcr_entry:
        stream_decls = {}
        for dcr_elem in _dict_elements(dcr_entry[1]):
            stream_decls.update(
                (dcr_elem.get("properties", {}) or {}).get("streamDeclarations", {}) or {}
            )
        for idx, element in enumerate(polling_elements):
            stream_name = (element.get("properties", {}) or {}).get("dcrConfig", {}).get("streamName")
            if not stream_name:
                continue
            if stream_name not in stream_decls:
                results.append(CheckResult(
                    f"polling.dcrConfig.streamName has matching DCR streamDeclaration",
                    False,
                    f"Polling element {idx} declares streamName {stream_name!r} "
                    f"but DCR streamDeclarations only has: {sorted(stream_decls.keys())}",
                    file_label=f"{polling_label} <-> {dcr_label}",
                ))

    # 2. polling.dataType matches at least one table name (across all table files)
    if polling_entry and table_entries:
        table_names = set()
        for _, tcontent in table_entries:
            tables = tcontent if isinstance(tcontent, list) else [tcontent]
            for t in tables:
                tn = t.get("name") or (t.get("properties", {}) or {}).get("schema", {}).get("name")
                if tn:
                    table_names.add(tn)
        for idx, element in enumerate(polling_elements):
            data_type = (element.get("properties", {}) or {}).get("dataType")
            if not data_type:
                continue
            if data_type not in table_names:
                results.append(CheckResult(
                    f"polling.dataType matches a table name",
                    False,
                    f"Polling element {idx} dataType {data_type!r} doesn't match "
                    f"any table (have: {sorted(table_names)})",
                    file_label=f"{polling_label} <-> tables",
                ))

    # 3. polling.connectorDefinitionName matches connector_definition.name
    if polling_entry and cd_entry:
        cd_content = _first_dict(cd_entry[1])
        if cd_content is not None:
            cd_name = cd_content.get("name")
            seen_cdnames = set()
            for idx, element in enumerate(polling_elements):
                cdn = (element.get("properties", {}) or {}).get("connectorDefinitionName")
                if not cdn:
                    continue
                seen_cdnames.add(cdn)
                if cd_name and cdn != cd_name:
                    results.append(CheckResult(
                        f"polling.connectorDefinitionName matches connector definition",
                        False,
                        f"Polling element {idx} connectorDefinitionName={cdn!r} != "
                        f"connector definition name {cd_name!r}",
                        file_label=f"{polling_entry[0].name} <-> {cd_entry[0].name}",
                    ))
            # All polling elements should share the same connectorDefinitionName
            if len(seen_cdnames) > 1:
                results.append(CheckResult(
                    f"All polling elements share connectorDefinitionName",
                    False,
                    f"Multiple values seen: {sorted(seen_cdnames)} -- for a single "
                    f"connector all array elements must use the same value",
                    file_label=polling_label,
                ))

    # 4. instructionSteps Textbox names cover polling {{placeholders}}
    if polling_entry and cd_entry:
        cd_content = _first_dict(cd_entry[1])
        if cd_content is not None:
            ui = (cd_content.get("properties", {}) or {}).get("connectorUiConfig", {}) or {}
            steps = ui.get("instructionSteps", []) or []
            textbox_names = _collect_textbox_names(steps)
            placeholders = set()
            for el in polling_elements:
                placeholders |= _collect_placeholders(el)
            missing = (placeholders - IMPLICIT_PLACEHOLDERS) - textbox_names
            if missing:
                results.append(CheckResult(
                    "Every polling {{placeholder}} has a matching Textbox name",
                    False,
                    f"Placeholders without matching Textbox: {sorted(missing)}. "
                    f"Add a Textbox with name=<placeholder> + validations.required:true.",
                    file_label=f"{polling_label} <-> {cd_entry[0].name}",
                ))
            # Skip the "extras" warning when the polling file uses ARM-style
            # parameter references — the binding goes via ARM, not Textbox name,
            # so any unreferenced Textbox in the placeholder set is a false alarm.
            uses_arm_binding = any(_has_arm_param_references(el) for el in polling_elements)
            extras = textbox_names - placeholders - {"clientId", "clientSecret"}
            if extras and not uses_arm_binding:
                results.append(CheckResult(
                    "All Textbox names are referenced by polling config",
                    True,
                    f"Textbox names with no matching {{{{placeholder}}}}: "
                    f"{sorted(extras)}. These won't bind to anything.",
                    warning=True,
                    file_label=f"{polling_label} <-> {cd_entry[0].name}",
                ))

    return results


# ---------------------------------------------------------------------------
# CLI + orchestration
# ---------------------------------------------------------------------------

def resolve_files(args: argparse.Namespace) -> list[Path]:
    paths = []
    if args.folder:
        folder = Path(args.folder).resolve()
        if not folder.is_dir():
            sys.stderr.write(f"ERROR: --folder is not a directory: {folder}\n")
            sys.exit(2)
        paths = sorted(folder.glob("*.json"))
    paths.extend(Path(p).resolve() for p in args.files)
    if not paths:
        sys.stderr.write("ERROR: no input files; provide file paths or --folder\n")
        sys.exit(2)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Microsoft Sentinel CCF source files (polling config, DCR, table, connector definition).",
    )
    parser.add_argument("files", nargs="*", help="Paths to CCF source files")
    parser.add_argument("--folder", help="Validate all *.json files in this directory")
    parser.add_argument("--verbose", action="store_true", help="Show all checks (default: only failures and warnings)")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures (affects exit code only)")
    args = parser.parse_args()

    paths = resolve_files(args)
    schemas = load_schemas()

    # Load and classify each file. Tables can appear multiple times (one per
    # table); polling / DCR / connector definition / push expect at most one.
    by_kind: dict[str, list[tuple[Path, Union[dict, list]]]] = {
        "polling": [], "push": [], "dcr": [], "table": [], "connector_definition": [],
    }
    all_results: list[CheckResult] = []
    unknown_files: list[Path] = []

    for path in paths:
        content, err = load_json_file(path)
        if err:
            all_results.append(CheckResult(
                "JSON syntax valid", False, err, file_label=path.name,
            ))
            continue
        kind = classify_file(content)
        if kind is None:
            unknown_files.append(path)
            continue
        if kind != "table" and by_kind[kind]:
            sys.stderr.write(
                f"WARNING: multiple {kind} files provided; using "
                f"{by_kind[kind][0][0].name}, skipping {path.name}\n"
            )
            continue
        by_kind[kind].append((path, content))

    # Schema + domain checks per file
    for kind, entries in by_kind.items():
        for path, content in entries:
            label = path.name
            if kind in schemas:
                all_results.extend(run_schema_validation(content, schemas[kind], label))
            else:
                # Push has no bundled schema -- note it explicitly
                all_results.append(CheckResult(
                    "JSON Schema valid",
                    True,
                    "Push connector kind: bundled schema does not cover Push; "
                    "running domain + cross-file checks only.",
                    warning=True,
                    file_label=label,
                ))
            if kind == "polling":
                all_results.extend(check_polling_domain(content, label))
            elif kind == "push":
                all_results.extend(check_push_domain(content, label))
            elif kind == "table":
                all_results.extend(check_table_domain(content, label))
            elif kind == "dcr":
                for elem in _dict_elements(content):
                    all_results.extend(check_dcr_domain(elem, label))
            elif kind == "connector_definition":
                for elem in _dict_elements(content):
                    all_results.extend(check_connector_definition_domain(elem, label))

    # Cross-file checks
    populated_kinds = [k for k, v in by_kind.items() if v]
    if len(populated_kinds) >= 2:
        all_results.extend(cross_file_checks(by_kind))

    # Warn if both polling and push present (a connector folder usually has one or the other)
    if by_kind["polling"] and by_kind["push"]:
        all_results.append(CheckResult(
            "Connector folder contains either polling OR push (not both)",
            True,
            f"Found both a polling config and a push connector definition; "
            f"a single connector folder usually contains one or the other.",
            warning=True,
        ))

    # Report
    print(f"\nCCF Source-File Validator")
    print(f"=========================")
    for kind, entries in by_kind.items():
        for path, _ in entries:
            print(f"  {KIND_LABELS[kind]:25} {path}")
    for path in unknown_files:
        print(f"  UNRECOGNIZED              {path}  (not a CCF source file)")
    print()

    show = [r for r in all_results if args.verbose or not r.passed or r.warning]
    for r in show:
        print(r)

    failures = [r for r in all_results if not r.passed]
    warnings = [r for r in all_results if r.warning]
    passes = [r for r in all_results if r.passed and not r.warning]

    print()
    print(f"Summary: {len(passes)} pass, {len(warnings)} warn, {len(failures)} fail")
    if unknown_files:
        print(f"         {len(unknown_files)} file(s) not recognized as CCF source files")

    if failures:
        return 1
    if args.strict and warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
