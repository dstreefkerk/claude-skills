#!/usr/bin/env python3
"""
CCF Connector ARM Template Validator

Validates a Microsoft Sentinel Codeless Connector Framework (CCF) ARM template
against the deployment checklist. Run after generating any new connector template.

Usage:
    python validate_connector.py mainTemplate.json
    python validate_connector.py mainTemplate.json --verbose
    python validate_connector.py mainTemplate.json --connector-type push
"""

import json
import re
import sys
import os
from pathlib import Path


# --- Blocked KQL functions/operators ---
BLOCKED_KQL_FUNCTIONS = [
    "coalesce", "replace_string", "replace_regex",
    "bag_keys", "bag_values", "bag_set", "bag_remove_keys",
]
BLOCKED_KQL_OPERATORS = [
    "summarize", "join", "union", "mv-expand", "mv-apply",
    "top ", "sort ", "distinct", "invoke", "scan", "partition",
    "project-reorder", "parse_csv",
]

# --- Reserved table column names (case-insensitive) ---
RESERVED_TABLE_COLUMN_NAMES = {
    "id", "billedsize", "isbillable", "invalidtimegenerated",
    "tenantid", "title", "type", "uniqueid",
    "_itemid", "_resourcegroup", "_resourceid",
    "_subscriptionid", "_timereceived",
}

# --- Expected resource types ---
EXPECTED_RESOURCE_TYPES = {
    "Microsoft.OperationalInsights/workspaces/providers/contentPackages",
    "Microsoft.OperationalInsights/workspaces/providers/contentTemplates",
    "Microsoft.OperationalInsights/workspaces/providers/dataConnectorDefinitions",
    "Microsoft.OperationalInsights/workspaces/providers/metadata",
}

# --- Valid connector kinds (case-insensitive) ---
VALID_CONNECTOR_KINDS = {
    "restapipoller", "websocket", "gcp", "amazonwebservicess3",
    "push", "storageaccountblobcontainer", "oci", "purviewaudit",
}

# --- Known standard Microsoft-* output streams ---
# Extracted from standardLogStreams.ps1 (unique Value entries)
KNOWN_STANDARD_STREAMS = {
    "Microsoft-ABAPAuditLog",
    "Microsoft-Alert",
    "Microsoft-AlertEvidence",
    "Microsoft-AlertInfo",
    "Microsoft-Anomalies",
    "Microsoft-AppCenterError",
    "Microsoft-ASimAuditEventLogs",
    "Microsoft-ASimAuthenticationEventLogs",
    "Microsoft-ASimDhcpEventLogs",
    "Microsoft-ASimDnsActivityLogs",
    "Microsoft-ASimFileEventLogs",
    "Microsoft-ASimNetworkSessionLogs",
    "Microsoft-ASimProcessEventLogs",
    "Microsoft-ASimRegistryEventLogs",
    "Microsoft-ASimUserManagementActivityLogs",
    "Microsoft-ASimWebSessionLogs",
    "Microsoft-AWSCloudTrail",
    "Microsoft-AWSCloudWatch",
    "Microsoft-AWSGuardDuty",
    "Microsoft-AWSNetworkFirewallAlert",
    "Microsoft-AWSNetworkFirewallFlow",
    "Microsoft-AWSNetworkFirewallTls",
    "Microsoft-AWSRoute53Resolver",
    "Microsoft-AWSS3ServerAccess",
    "Microsoft-AWSSecurityHubFindings",
    "Microsoft-AWSVPCFlow",
    "Microsoft-AWSWAF",
    "Microsoft-CloudAppEvents",
    "Microsoft-CommonSecurityLog",
    "Microsoft-ComputerGroup",
    "Microsoft-CopilotActivity",
    "Microsoft-DataverseActivity",
    "Microsoft-DeviceEvents",
    "Microsoft-DeviceFileCertificateInfo",
    "Microsoft-DeviceFileEvents",
    "Microsoft-DeviceImageLoadEvents",
    "Microsoft-DeviceInfo",
    "Microsoft-DeviceLogonEvents",
    "Microsoft-DeviceNetworkEvents",
    "Microsoft-DeviceNetworkInfo",
    "Microsoft-DeviceProcessEvents",
    "Microsoft-DeviceRegistryEvents",
    "Microsoft-DeviceTvmSecureConfigurationAssessment",
    "Microsoft-DeviceTvmSecureConfigurationAssessmentKB",
    "Microsoft-DeviceTvmSoftwareInventory",
    "Microsoft-DeviceTvmSoftwareVulnerabilities",
    "Microsoft-DeviceTvmSoftwareVulnerabilitiesKB",
    "Microsoft-DnsAuditEvents",
    "Microsoft-DnsEvents",
    "Microsoft-DnsInventory",
    "Microsoft-Dynamics365Activity",
    "Microsoft-EmailAttachmentInfo",
    "Microsoft-EmailEvents",
    "Microsoft-EmailPostDeliveryEvents",
    "Microsoft-EmailUrlInfo",
    "Microsoft-GCPApigee",
    "Microsoft-GCPAuditLogs",
    "Microsoft-GCPCDN",
    "Microsoft-GCPCloudRun",
    "Microsoft-GCPCloudSQL",
    "Microsoft-GCPComputeEngine",
    "Microsoft-GCPDNS",
    "Microsoft-GCPFirewallLogs",
    "Microsoft-GCPIAM",
    "Microsoft-GCPIDS",
    "Microsoft-GCPLoadBalancer",
    "Microsoft-GCPMonitoring",
    "Microsoft-GCPNAT",
    "Microsoft-GCPNATAudit",
    "Microsoft-GCPResourceManager",
    "Microsoft-GCPVPCFlow",
    "Microsoft-GKEAPIServer",
    "Microsoft-GKEApplication",
    "Microsoft-GKEAudit",
    "Microsoft-GKEControllerManager",
    "Microsoft-GKEHPADecision",
    "Microsoft-GKEScheduler",
    "Microsoft-GoogleCloudSCC",
    "Microsoft-GoogleWorkspaceReports",
    "Microsoft-HuntingBookmark",
    "Microsoft-IdentityDirectoryEvents",
    "Microsoft-IdentityLogonEvents",
    "Microsoft-IdentityQueryEvents",
    "Microsoft-IlumioInsights",
    "Microsoft-InsightsMetrics",
    "Microsoft-LinuxAuditLog",
    "Microsoft-McasShadowItReporting",
    "Microsoft-MicrosoftPurviewInformationProtection",
    "Microsoft-OfficeActivity",
    "Microsoft-Operation",
    "Microsoft-PowerAppsActivity",
    "Microsoft-PowerAutomateActivity",
    "Microsoft-PowerBIActivity",
    "Microsoft-PowerPlatformAdminActivity",
    "Microsoft-PowerPlatformConnectorActivity",
    "Microsoft-PowerPlatformDlpActivity",
    "Microsoft-ProjectActivity",
    "Microsoft-SecurityAlert",
    "Microsoft-SecurityEvent",
    "Microsoft-SecurityIncident",
    "Microsoft-SentinelCrowdStrikeAlerts",
    "Microsoft-SentinelCrowdStrikeDetections",
    "Microsoft-SentinelCrowdStrikeHosts",
    "Microsoft-SentinelCrowdStrikeIncidents",
    "Microsoft-SentinelCrowdStrikeVulnerabilities",
    "Microsoft-SentinelHealth",
    "Microsoft-ThreatIntelligenceIndicator",
    "Microsoft-UrlClickEvents",
    "Microsoft-Usage",
    "Microsoft-Watchlist",
    "Microsoft-WindowsEvent",
}


class CheckResult:
    def __init__(self, name, passed, message="", warning=False):
        self.name = name
        self.passed = passed
        self.message = message
        self.warning = warning

    def __str__(self):
        if self.warning:
            status = "WARN"
        else:
            status = "PASS" if self.passed else "FAIL"
        msg = f"  {status}  {self.name}"
        if self.message:
            msg += f"\n        {self.message}"
        return msg


def load_template(path):
    """Load and parse the ARM template JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_resources_by_type(resources, rtype):
    """Find all resources matching a given type."""
    return [r for r in resources if r.get("type", "") == rtype]


def find_nested_templates(resources):
    """Extract nested mainTemplate blocks from contentTemplates resources."""
    results = []
    for r in resources:
        if r.get("type", "").endswith("contentTemplates"):
            mt = r.get("properties", {}).get("mainTemplate")
            if mt:
                kind = r.get("properties", {}).get("contentKind", "unknown")
                results.append({"kind": kind, "mainTemplate": mt, "parent": r})
    return results


def resolve_arm_variable(expr, template):
    """Try to resolve a simple ARM variable reference like [variables('name')].

    Returns the resolved string value, or None if it can't be resolved.
    """
    m = re.match(r"^\[variables\('([^']+)'\)\]$", expr)
    if m:
        var_name = m.group(1)
        return template.get("variables", {}).get(var_name)
    return None


def json_deep_strings(obj, path=""):
    """Yield (path, string_value) for every string in a nested JSON structure."""
    if isinstance(obj, str):
        yield (path, obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from json_deep_strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from json_deep_strings(v, f"{path}[{i}]")


def get_prop_ci(obj, name):
    """Case-insensitive property lookup on a dict. Returns (key, value) or (None, None)."""
    if not isinstance(obj, dict):
        return None, None
    name_lower = name.lower()
    for k, v in obj.items():
        if k.lower() == name_lower:
            return k, v
    return None, None


def find_poller_resources(template):
    """Find all connector poller resources (any kind) inside ResourcesDataConnector nested templates.

    Returns list of (resource_dict, nested_template_dict) tuples.
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    results = []
    for nt in nested:
        if nt["kind"] == "ResourcesDataConnector":
            for res in nt["mainTemplate"].get("resources", []):
                if res.get("kind"):
                    results.append((res, nt["mainTemplate"]))
    return results


def collect_instruction_types(instruction_steps):
    """Recursively collect (type, parameters) from instruction steps."""
    results = []
    if not isinstance(instruction_steps, list):
        return results
    for step in instruction_steps:
        instructions = step.get("instructions", [])
        if not isinstance(instructions, list):
            continue
        for instr in instructions:
            itype = instr.get("type", "")
            params = instr.get("parameters", {})
            results.append((itype, params))
            # Recurse into ContextPane
            if itype == "ContextPane":
                inner_steps = params.get("instructionSteps", [])
                if isinstance(inner_steps, list):
                    results.extend(collect_instruction_types(inner_steps))
    return results


# ============================================================
# Individual checks
# ============================================================

def check_json_valid(path):
    """Check 0: JSON is valid."""
    try:
        load_template(path)
        return CheckResult("JSON syntax valid", True)
    except json.JSONDecodeError as e:
        return CheckResult("JSON syntax valid", False, str(e))


def check_resource_count(template):
    """Check 1: Required CCF resource types are present.

    Solutions may contain many contentTemplates (workbooks, analytics, etc.)
    and the packager may duplicate connector resources for multi-poller setups.
    We check minimums, not exact counts.
    """
    resources = template.get("resources", [])
    types_found = [r.get("type", "") for r in resources]

    content_templates = [t for t in types_found if t.endswith("contentTemplates")]
    content_packages = [t for t in types_found if t.endswith("contentPackages")]
    definitions = [t for t in types_found if t.endswith("dataConnectorDefinitions")]
    metadata = [t for t in types_found if t.endswith("metadata")]

    issues = []
    if len(content_packages) < 1:
        issues.append(f"Expected >=1 contentPackages, found {len(content_packages)}")
    if len(content_templates) < 2:
        issues.append(f"Expected >=2 contentTemplates, found {len(content_templates)}")
    if len(definitions) < 1:
        issues.append(f"Expected >=1 dataConnectorDefinitions, found {len(definitions)}")
    if len(metadata) < 1:
        issues.append(f"Expected >=1 metadata, found {len(metadata)}")

    if issues:
        return CheckResult("Required CCF resource types present", False, "; ".join(issues))
    return CheckResult("Required CCF resource types present", True,
                        f"{len(resources)} resources total")


def check_solution_version(template):
    """Check 2: Solution version >= 3.0.0."""
    variables = template.get("variables", {})
    version = variables.get("_solutionVersion", "")
    if not version:
        return CheckResult("Solution version >= 3.0.0", False, "_solutionVersion not found")
    try:
        parts = [int(x) for x in version.split(".")]
        if parts[0] >= 3:
            return CheckResult("Solution version >= 3.0.0", True, f"v{version}")
        return CheckResult("Solution version >= 3.0.0", False, f"v{version} < 3.0.0")
    except (ValueError, IndexError):
        return CheckResult("Solution version >= 3.0.0", False, f"Cannot parse: {version}")


def check_content_packages_properties(template):
    """Check 3: contentPackages has contentProductId and packageId."""
    resources = template.get("resources", [])
    pkgs = find_resources_by_type(resources,
        "Microsoft.OperationalInsights/workspaces/providers/contentPackages")
    if not pkgs:
        return CheckResult("contentPackages has required properties", False,
                           "No contentPackages resource found")
    props = pkgs[0].get("properties", {})
    missing = []
    if "contentProductId" not in props:
        missing.append("contentProductId")
    # packageId OR contentProductId is sufficient (packager uses contentProductId)
    if "packageId" not in props and "contentProductId" not in props:
        missing.append("packageId or contentProductId")
    if missing:
        return CheckResult("contentPackages has required properties", False,
                           f"Missing: {', '.join(missing)}")
    return CheckResult("contentPackages has required properties", True)


def check_depends_on(template):
    """Check 4: contentTemplates depend on contentPackages.

    Only contentTemplates are required to have dependsOn pointing at the
    contentPackages resource. Live resources (dataConnectorDefinitions,
    metadata, savedSearches, dataConnectors) are top-level and don't need
    dependsOn  -- the packager deliberately omits it on them.
    """
    resources = template.get("resources", [])
    issues = []
    for r in resources:
        rtype = r.get("type", "")
        if not rtype.endswith("contentTemplates"):
            continue
        deps = r.get("dependsOn", [])
        if not deps:
            issues.append(f"contentTemplates has no dependsOn")
        else:
            has_pkg_dep = any("contentPackages" in str(d) for d in deps)
            if not has_pkg_dep:
                issues.append(f"contentTemplates doesn't dependsOn contentPackages")
    if issues:
        return CheckResult("Dependency chain valid", False, "; ".join(issues))
    return CheckResult("Dependency chain valid", True)


def check_bracket_escaping(template):
    """Check 5: Bracket escaping correct per content template type.

    - DataConnector contentTemplates (deploy-time): single brackets [expr] are correct
    - ResourcesDataConnector contentTemplates (connect-time): must use double brackets [[expr]

    Exceptions (single brackets OK in connect-time templates):
    - Parameter defaultValue fields  -- these are deploy-time expressions that
      pass outer parameter values into the nested template
    - Variables section  -- variable definitions reference outer-scope variables
    - $schema and contentVersion fields
    - Outer-scope variable references  -- [variables('x')] where x is defined
      in the parent template but NOT in the nested template's own variables
      section. These are intentional deploy-time injections that bake literal
      values into the connect-time template.
    - format()/concat() calls  -- always deploy-time evaluations
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    parent_vars = template.get("variables", {})
    issues = []

    for nt in nested:
        mt = nt["mainTemplate"]
        kind = nt["kind"]

        # Only check connect-time templates (ResourcesDataConnector)
        # Deploy-time templates (DataConnector) correctly use single brackets
        if kind != "ResourcesDataConnector":
            continue

        nested_vars = mt.get("variables", {})

        # Identify which nested resource indices are metadata (deploy-time)
        # vs data connectors (connect-time). Only check connect-time resources.
        mt_resources = mt.get("resources", [])
        connect_time_indices = set()
        for ri, res in enumerate(mt_resources):
            res_type = res.get("type", "")
            # metadata resources inside connections templates use single brackets
            # (deploy-time evaluation)  -- this is the packager's deliberate pattern
            if res_type.endswith("/metadata"):
                continue
            connect_time_indices.add(ri)

        for path, val in json_deep_strings(mt):
            if not isinstance(val, str):
                continue
            if not val.startswith("[") or val.startswith("[["):
                continue
            # Skip metadata fields
            if path.endswith(".$schema") or path.endswith(".contentVersion"):
                continue
            # Skip parameter defaults  -- these are deploy-time expressions
            # that pass outer parameter values into the nested template
            if ".parameters." in path and path.endswith(".defaultValue"):
                continue
            # Skip variables section  -- variable definitions reference outer scope
            if ".variables." in path or path.startswith(".variables."):
                continue
            # Skip outer-scope variable references -- [variables('x')] where x
            # is defined in the parent template but NOT in the nested template.
            # These are intentional deploy-time injections (7 production connectors
            # use this pattern: AWS_AccessLogs, BigID, Check Point CloudGuard, etc.)
            var_match = re.match(r"^\[variables\('([^']+)'\)\]$", val)
            if var_match:
                var_name = var_match.group(1)
                if var_name not in nested_vars:
                    continue  # Outer-scope variable -- deploy-time injection
            # Skip format() and concat() calls -- always deploy-time evaluations
            if val.startswith("[format(") or val.startswith("[concat("):
                continue
            # Skip metadata resources inside connections templates
            # (they are deploy-time, not connect-time)
            res_idx_match = re.match(r'^\.resources\[(\d+)\]', path)
            if res_idx_match:
                idx = int(res_idx_match.group(1))
                if idx not in connect_time_indices:
                    continue
                # Within connect-time resources, skip top-level resource fields
                # (name, location, kind, apiVersion, dependsOn, tags) which are
                # deploy-time even on data connector resources
                after_idx = path[res_idx_match.end():]
                deploy_time_prefixes = (
                    ".name", ".location", ".kind", ".apiVersion",
                    ".dependsOn", ".tags", ".type",
                )
                if any(after_idx == prefix or after_idx.startswith(prefix + "[")
                       or after_idx.startswith(prefix + ".")
                       for prefix in deploy_time_prefixes):
                    continue

            short_path = path.split(".", 2)[-1] if path.count(".") > 1 else path
            issues.append(f"{kind}: single bracket at {short_path}: {val[:60]}")

    if issues:
        return CheckResult("Bracket escaping in nested templates", False,
                           f"{len(issues)} single-bracket expression(s) found:\n        " +
                           "\n        ".join(issues[:5]))
    return CheckResult("Bracket escaping in nested templates", True,
                        f"Checked {len(nested)} nested template(s)")


def check_definition_template_depends_on(template):
    """Check 43: ConnectorDefinition contentTemplate must depend only on contentPackages.

    The ConnectorDefinition contentTemplate (contentKind: "DataConnector") must
    NOT have a dependsOn entry referencing the Connections contentTemplate
    (contentKind: "ResourcesDataConnector"). A reversed dependency causes
    "content template $XxxDefinition not found" at Connect time because the
    Portal cannot locate the definition template.
    """
    resources = template.get("resources", [])
    issues = []

    for r in resources:
        if not r.get("type", "").endswith("contentTemplates"):
            continue
        content_kind = r.get("properties", {}).get("contentKind", "")
        if content_kind != "DataConnector":
            continue

        deps = r.get("dependsOn", [])
        for dep in deps:
            dep_str = str(dep)
            if "contentTemplates" in dep_str:
                issues.append(
                    "ConnectorDefinition contentTemplate must depend only on "
                    "contentPackages, not on Connections contentTemplate. "
                    "Found dependsOn referencing contentTemplates: "
                    f"{dep_str[:100]}")

    if issues:
        return CheckResult("Definition template depends only on contentPackages",
                           False, "; ".join(issues))
    return CheckResult("Definition template depends only on contentPackages", True)


def check_connections_content_product_id_prefix(template):
    """Check 44: Connections contentProductId must use 'rdc' prefix.

    The contentProductId on the Connections contentTemplate (contentKind:
    "ResourcesDataConnector") must use the 'rdc' prefix, not 'dc'. Using
    'dc' causes the Portal to look in the wrong content category, leading
    to "content template not found" errors.

    Prefix conventions:
    - 'sl' for Solution (contentPackages)
    - 'dc' for DataConnector (ConnectorDefinition contentTemplate)
    - 'rdc' for ResourcesDataConnector (Connections contentTemplate)
    """
    resources = template.get("resources", [])
    issues = []

    for r in resources:
        if not r.get("type", "").endswith("contentTemplates"):
            continue
        props = r.get("properties", {})
        content_kind = props.get("contentKind", "")
        if content_kind != "ResourcesDataConnector":
            continue

        cpid = props.get("contentProductId", "")
        if not cpid:
            continue

        # Check for the wrong prefix pattern: '-','dc','- (should be '-','rdc','-')
        # Look for the literal string pattern in the ARM expression
        if "'-','dc','-'" in cpid or "'-', 'dc', '-'" in cpid:
            issues.append(
                "Connections contentProductId should use 'rdc' prefix "
                "(ResourcesDataConnector), not 'dc'. Found: "
                f"{cpid[:120]}")
        # Also check for common concat patterns without spaces
        elif "'dc'" in cpid and "'rdc'" not in cpid:
            # More flexible check: has 'dc' but not 'rdc'
            issues.append(
                "Connections contentProductId should use 'rdc' prefix "
                "(ResourcesDataConnector), not 'dc'. Found: "
                f"{cpid[:120]}")

    if issues:
        return CheckResult("Connections contentProductId uses 'rdc' prefix",
                           False, "; ".join(issues))
    return CheckResult("Connections contentProductId uses 'rdc' prefix", True)


def check_connections_metadata_parent_id(template):
    """Check 45: Connections metadata parentId references an existing resource.

    The metadata resource inside the ResourcesDataConnector nested template
    has a parentId that must reference an actually-deployed resource. For
    multi-poller connectors, the parentId should reference the
    dataConnectorDefinitions resource (which always exists), not a specific
    dataConnectors/<name> resource that may not exist.
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    # Collect known definition IDs for reference
    definition_ids = set()
    for nt in nested:
        if nt["kind"] == "DataConnector":
            for res in nt["mainTemplate"].get("resources", []):
                if res.get("type", "").endswith("dataConnectorDefinitions"):
                    ui_id = res.get("properties", {}).get(
                        "connectorUiConfig", {}).get("id", "")
                    if ui_id:
                        resolved = resolve_arm_variable(
                            ui_id, template) if ui_id.startswith("[") else ui_id
                        if resolved:
                            definition_ids.add(resolved)

    # Collect poller resource names from ResourcesDataConnector templates
    poller_names = set()
    for nt in nested:
        if nt["kind"] == "ResourcesDataConnector":
            for res in nt["mainTemplate"].get("resources", []):
                res_kind = res.get("kind", "")
                if res_kind and res_kind.lower() in VALID_CONNECTOR_KINDS:
                    name = res.get("name", "")
                    if name:
                        # Extract the last segment (after the last /)
                        short = name.split("/")[-1].strip("']\"")
                        poller_names.add(short)

    # Check metadata parentId in ResourcesDataConnector templates
    for nt in nested:
        if nt["kind"] != "ResourcesDataConnector":
            continue
        for res in nt["mainTemplate"].get("resources", []):
            if not res.get("type", "").endswith("/metadata"):
                continue
            parent_id = res.get("properties", {}).get("parentId", "")
            if not parent_id:
                continue

            # Check if parentId references dataConnectors (not dataConnectorDefinitions)
            if "dataConnectors/" in parent_id and "dataConnectorDefinitions/" not in parent_id:
                # Extract the connector name from the parentId
                m = re.search(r"dataConnectors/[^'\")\]]*?([^/'\")\]]+)", parent_id)
                connector_name = m.group(1) if m else "unknown"
                # This is a warning -- it works for single-poller but fails for multi-poller
                if len(poller_names) > 1:
                    issues.append(
                        f"Connections metadata parentId references "
                        f"dataConnectors/'{connector_name}' but this is a "
                        f"multi-poller connector with {len(poller_names)} "
                        f"pollers. For multi-poller connectors, parentId "
                        f"should reference dataConnectorDefinitions instead.")

    if issues:
        return CheckResult("Connections metadata parentId valid", True,
                           "; ".join(issues), warning=True)
    return CheckResult("Connections metadata parentId valid", True)


def check_nested_table_no_kind_or_location(template):
    """Check 46: Table resources inside contentTemplate mainTemplate should not
    have non-null 'kind' properties.

    Tables inside nested mainTemplate blocks are stored definitions for
    Content Hub. "kind": null is the standard Microsoft packager pattern
    (used by 81/110 production connectors) and is harmless -- ARM treats
    null the same as omission. "location" is also universally present in
    production connectors and does not cause deployment failures.

    Only flag genuinely wrong non-null kind values.
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    for nt in nested:
        mt = nt["mainTemplate"]
        for res in mt.get("resources", []):
            if not res.get("type", "").endswith("/tables"):
                continue

            table_name = res.get("name", "unknown")
            resolved = resolve_arm_variable(
                table_name, template) if table_name.startswith("[") else table_name

            display_name = resolved or table_name
            if len(display_name) > 60:
                display_name = display_name[:60] + "..."

            # Only flag non-null kind values -- "kind": null is the standard
            # production pattern (81/110 connectors) and is harmless
            if "kind" in res and res["kind"] is not None:
                issues.append(
                    f"Table '{display_name}' inside contentTemplate "
                    f"mainTemplate has 'kind' property (value: "
                    f"{res['kind']!r}). Omit the 'kind' property or set "
                    f"it to null for tables inside nested templates.")

            # Note: "location" is NOT flagged -- every production connector
            # includes it on nested tables and it does not cause issues.

    if issues:
        return CheckResult(
            "Nested tables have no non-null kind", False,
            "; ".join(issues))
    return CheckResult("Nested tables have no non-null kind", True)


def check_top_level_tables_exist(template):
    """Check 47: Custom tables should also exist as top-level ARM resources.

    Tables defined only inside contentTemplate mainTemplate are stored
    definitions -- they are NOT actually created during ARM deployment. When
    the Connect button creates the DCR, it references tables that must already
    exist. Without top-level table resources, the Connect button fails with:
      InvalidOutputTable: Table not available for destination

    This check collects table names from DCR outputStream references and
    verifies that matching top-level table resources exist.
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)

    # Collect custom table names from DCR outputStream (strip Custom- prefix)
    dcr_table_names = set()
    for nt in nested:
        if nt["kind"] == "DataConnector":
            for res in nt["mainTemplate"].get("resources", []):
                if res.get("type", "").endswith("dataCollectionRules"):
                    for flow in res.get("properties", {}).get("dataFlows", []):
                        output = flow.get("outputStream", "")
                        if output.startswith("Custom-"):
                            dcr_table_names.add(output.replace("Custom-", "", 1))

    if not dcr_table_names:
        return CheckResult("Top-level tables exist for DCR outputs", True,
                           "No Custom-* output streams found")

    # Collect top-level table resource names (outside contentTemplates)
    top_level_tables = set()
    for r in resources:
        if r.get("type", "").endswith("/tables") and not r.get("type", "").endswith("contentTemplates"):
            name = r.get("name", "")
            resolved = resolve_arm_variable(
                name, template) if name.startswith("[") else name
            if resolved:
                # Extract table name (last segment after /)
                table_part = resolved.split("/")[-1]
                top_level_tables.add(table_part)
            # Also check schema name
            schema_name = r.get("properties", {}).get("schema", {}).get("name", "")
            if schema_name:
                top_level_tables.add(schema_name.split("/")[-1])

    # Check which DCR tables are missing from top-level
    missing = dcr_table_names - top_level_tables
    if missing:
        return CheckResult(
            "Top-level tables exist for DCR outputs", True,
            f"Custom tables should also be deployed as top-level resources "
            f"to prevent InvalidOutputTable errors at Connect time. "
            f"Missing top-level tables: {sorted(missing)}",
            warning=True)
    return CheckResult("Top-level tables exist for DCR outputs", True,
                        f"All {len(dcr_table_names)} DCR output tables have "
                        f"top-level resources")


def check_deploy_time_double_brackets(template):
    """Check 39: Double-bracket expressions in deploy-time (DataConnector) nested templates.

    DataConnector contentTemplates are evaluated at deploy time, so ARM expressions
    must use single brackets [expr]. Double brackets [[expr]] cause ARM to store the
    literal string instead of evaluating it  -- e.g. location gets the literal text
    "[parameters('location')]" instead of the actual Azure region.

    Metadata resources are excluded because they are packager-managed content that
    may legitimately use [[expr]] for deferred content-hub evaluation.
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    for nt in nested:
        mt = nt["mainTemplate"]
        kind = nt["kind"]

        # Only check deploy-time templates (DataConnector)
        if kind != "DataConnector":
            continue

        mt_resources = mt.get("resources", [])
        # Identify non-metadata resource indices (deploy-time resources
        # that should use single brackets)
        deploy_indices = set()
        for ri, res in enumerate(mt_resources):
            res_type = res.get("type", "")
            if not res_type.endswith("/metadata"):
                deploy_indices.add(ri)

        for path, val in json_deep_strings(mt):
            if not isinstance(val, str):
                continue
            if not val.startswith("[["):
                continue
            # Skip metadata fields
            if path.endswith(".$schema") or path.endswith(".contentVersion"):
                continue
            # Only flag [[expr]] inside non-metadata resources
            res_idx_match = re.match(r'^\.resources\[(\d+)\]', path)
            if res_idx_match:
                idx = int(res_idx_match.group(1))
                if idx not in deploy_indices:
                    continue
            else:
                # Top-level template strings outside resources  -- skip
                continue

            short_path = path.split(".", 2)[-1] if path.count(".") > 1 else path
            issues.append(
                f"DataConnector: double bracket at {short_path}: {val[:60]}  "
                f"-> use single bracket [expr] instead"
            )

    if issues:
        return CheckResult("Deploy-time double-bracket escaping", False,
                           f"{len(issues)} double-bracket expression(s) in deploy-time template(s):\n        " +
                           "\n        ".join(issues[:5]))
    return CheckResult("Deploy-time double-bracket escaping", True,
                        f"Checked {sum(1 for nt in nested if nt['kind'] == 'DataConnector')} deploy-time template(s)")


def check_stream_declarations(template):
    """Check 6: Stream names have Custom- prefix; warn if TimeGenerated is in raw stream.

    TimeGenerated in the stream declaration is acceptable when:
    - The transform is a passthrough ('source')  -- common for push connectors
    - The transform type-converts it with todatetime(TimeGenerated)
    - The transform creates it with now() or similar (Keeper pattern)
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []
    warnings = []

    for nt in nested:
        mt = nt["mainTemplate"]
        for res in mt.get("resources", []):
            if res.get("type", "").endswith("dataCollectionRules"):
                streams = res.get("properties", {}).get("streamDeclarations", {})
                transforms = {}
                for flow in res.get("properties", {}).get("dataFlows", []):
                    for s in flow.get("streams", []):
                        transforms[s] = flow.get("transformKql", "")

                for sname, sdef in streams.items():
                    if not sname.startswith("Custom-"):
                        issues.append(f"Stream '{sname}' missing Custom- prefix")
                    cols = sdef.get("columns", [])
                    for col in cols:
                        if col.get("name", "") == "TimeGenerated":
                            kql = transforms.get(sname, "")
                            # Passthrough 'source' transforms are fine  -- TimeGenerated
                            # flows through from the stream (common for push connectors)
                            if _is_passthrough_kql(kql):
                                continue
                            # If transform just type-converts TimeGenerated (todatetime),
                            # it's a passthrough from the API  -- warn, don't fail
                            if re.search(r'TimeGenerated\s*=\s*todatetime\s*\(\s*TimeGenerated\s*\)', kql):
                                warnings.append(
                                    f"Stream '{sname}' passes TimeGenerated from API "
                                    "(conventional pattern creates it in transform). "
                                    "No action needed  -- this is a valid pattern.")
                            # If transform explicitly handles TimeGenerated (e.g. now()),
                            # the stream declaration is redundant but not harmful  -- warn
                            elif "TimeGenerated" in kql:
                                warnings.append(
                                    f"Stream '{sname}' has TimeGenerated in both stream "
                                    "declaration and transform. No action needed  -- "
                                    "redundant but deploys and functions correctly.")
                            else:
                                warnings.append(
                                    f"Stream '{sname}' has 'TimeGenerated' in stream "
                                    "declaration but transform doesn't reference it. "
                                    "The API timestamp will be ignored; platform uses "
                                    "now() instead. Consider adding "
                                    "TimeGenerated = todatetime(TimeGenerated) to "
                                    "transform, or remove from stream declaration.")

    if issues:
        return CheckResult("Stream declarations valid", False, "; ".join(issues))
    if warnings:
        return CheckResult("Stream declarations valid", True,
                           "; ".join(warnings), warning=True)
    return CheckResult("Stream declarations valid", True)


def check_table_names(template):
    """Check 7: Tables have _CL suffix and no workspace prefix in names."""
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    for nt in nested:
        mt = nt["mainTemplate"]
        for res in mt.get("resources", []):
            if res.get("type", "").endswith("/tables"):
                name = res.get("name", "")

                # Try to resolve ARM variable references
                resolved = resolve_arm_variable(name, template) if name.startswith("[") else name

                if resolved:
                    if "/" in resolved:
                        issues.append(f"Table '{resolved}' has workspace prefix (should be table name only)")
                    if not resolved.endswith("_CL"):
                        issues.append(f"Table '{resolved}' missing _CL suffix")
                elif name.startswith("["):
                    # ARM expression we can't resolve  -- also check the table schema name
                    schema_name = res.get("properties", {}).get("schema", {}).get("name", "")
                    if schema_name:
                        if "/" in schema_name:
                            issues.append(f"Table schema name '{schema_name}' has workspace prefix")
                        if not schema_name.endswith("_CL"):
                            issues.append(f"Table schema name '{schema_name}' missing _CL suffix")
                else:
                    if "/" in name:
                        issues.append(f"Table '{name}' has workspace prefix (should be table name only)")
                    if not name.endswith("_CL"):
                        issues.append(f"Table '{name}' missing _CL suffix")

    if issues:
        return CheckResult("Table names valid", False, "; ".join(issues))
    return CheckResult("Table names valid", True)


def _is_passthrough_kql(kql):
    """Check if a transformKql is a passthrough (just 'source', possibly with whitespace)."""
    return kql.strip().lower() == "source"


def _is_platform_managed_flow(flow):
    """Check if a dataFlow uses only Microsoft-* standard streams (platform-managed)."""
    streams = flow.get("streams", [])
    if not streams:
        return False
    return all(s.startswith("Microsoft-") for s in streams)


def check_kql_transforms(template):
    """Check 8: KQL transforms produce TimeGenerated, use only supported functions.

    Passthrough transforms ('source') are valid  -- they pass all columns through
    unchanged from the stream declaration, including TimeGenerated if present.
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    for nt in nested:
        mt = nt["mainTemplate"]
        for res in mt.get("resources", []):
            if res.get("type", "").endswith("dataCollectionRules"):
                flows = res.get("properties", {}).get("dataFlows", [])
                for i, flow in enumerate(flows):
                    kql = flow.get("transformKql", "")
                    stream = flow.get("streams", ["?"])[0]
                    label = f"dataFlow[{i}] ({stream})"

                    if not kql:
                        if _is_platform_managed_flow(flow):
                            continue  # Platform-managed  -- valid, skip silently
                        issues.append(f"{label}: no transformKql (Custom-* streams require an explicit transform)")
                        continue

                    # Passthrough transforms ('source') are always valid  --
                    # all columns including TimeGenerated pass through unchanged
                    if _is_passthrough_kql(kql):
                        continue

                    # Check TimeGenerated
                    if "TimeGenerated" not in kql:
                        issues.append(f"{label}: missing TimeGenerated")

                    # Check blank lines (strip trailing whitespace first)
                    if "\n\n" in kql.rstrip():
                        issues.append(f"{label}: contains blank lines")

                    # Check blocked functions
                    kql_lower = kql.lower()
                    for func in BLOCKED_KQL_FUNCTIONS:
                        # Match function call pattern: func( or func (
                        if re.search(rf'\b{re.escape(func)}\s*\(', kql_lower):
                            issues.append(f"{label}: uses blocked function '{func}'")

                    # Check blocked operators
                    for op in BLOCKED_KQL_OPERATORS:
                        if re.search(rf'\|\s*{re.escape(op.strip())}', kql_lower):
                            issues.append(f"{label}: uses blocked operator '{op.strip()}'")

                    # Check dynamic() literal
                    if re.search(r'\bdynamic\s*\(', kql_lower):
                        issues.append(f"{label}: uses blocked 'dynamic()' literal (use parse_json)")

    if issues:
        return CheckResult("KQL transforms valid", False, "; ".join(issues))
    return CheckResult("KQL transforms valid", True)


def check_securestring(template):
    """Check 9: Credential parameters use securestring type.

    Uses case-insensitive comparison for the type value since ARM accepts
    both 'securestring' and 'SecureString'. Excludes parameters whose names
    indicate they hold a keyvault *name* (not a secret itself).
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []
    warnings = []

    credential_keywords = {"apikey", "password", "secret", "token", "credential", "key"}
    # Parameters that contain credential keywords only because of non-secret
    # context -- vault names, org identifiers, secret *names* (not values)
    non_secret_exclusions = {
        "keyvault", "key_vault", "vault_name", "vaultname",
        "secretname", "secret_name",  # holds vault secret name, not the secret
        "organizationkey", "orgkey", "org_key",  # org identifier, not a secret
    }

    for nt in nested:
        mt = nt["mainTemplate"]
        kind = nt["kind"]
        params = mt.get("parameters", {})
        for pname, pdef in params.items():
            ptype = pdef.get("type", "")
            name_lower = pname.lower()
            # Skip non-secret parameters that happen to contain credential keywords
            if any(ex in name_lower for ex in non_secret_exclusions):
                continue
            if any(kw in name_lower for kw in credential_keywords):
                if ptype.lower() != "securestring":
                    if kind == "ResourcesDataConnector":
                        warnings.append(
                            f"Parameter '{pname}' in connect-time template has type "
                            f"'{ptype}' instead of securestring. This parameter is in "
                            f"a nested (connect-time) template. If the outer template "
                            f"passes the value via a securestring parameter, the value "
                            f"chain is already protected. 7/109 production connectors "
                            f"use this pattern.")
                    else:
                        issues.append(
                            f"Parameter '{pname}' looks like a credential but type is "
                            f"'{ptype}' (should be securestring)")

    if issues:
        return CheckResult("Credentials use securestring", False, "; ".join(issues))
    if warnings:
        return CheckResult("Credentials use securestring", True,
                           "; ".join(warnings), warning=True)
    return CheckResult("Credentials use securestring", True)


def check_connector_kind(template):
    """Check 10: dataConnectorDefinitions has kind=Customizable."""
    resources = template.get("resources", [])
    defs = find_resources_by_type(resources,
        "Microsoft.OperationalInsights/workspaces/providers/dataConnectorDefinitions")
    if not defs:
        return CheckResult("Connector kind is Customizable", False,
                           "No dataConnectorDefinitions resource found")
    kind = defs[0].get("kind", "")
    if kind != "Customizable":
        return CheckResult("Connector kind is Customizable", False, f"kind='{kind}'")
    return CheckResult("Connector kind is Customizable", True)


def check_connectivity_criteria(template, connector_type="pull"):
    """Check 11: connectivityCriteria type is a valid value.

    Both 'HasDataConnectors' and 'IsConnectedQuery' are valid for pull and
    push connectors. Production connectors use both interchangeably (e.g.
    ZeroFox pull uses IsConnectedQuery; SAP LogServ push uses HasDataConnectors).
    """
    resources = template.get("resources", [])
    defs = find_resources_by_type(resources,
        "Microsoft.OperationalInsights/workspaces/providers/dataConnectorDefinitions")
    if not defs:
        return CheckResult("connectivityCriteria type valid", False,
                           "No dataConnectorDefinitions found")

    ui_config = defs[0].get("properties", {}).get("connectorUiConfig", {})
    criteria = ui_config.get("connectivityCriteria", [])
    if not criteria:
        return CheckResult("connectivityCriteria type valid", False,
                           "No connectivityCriteria defined")

    valid_types = {"HasDataConnectors", "IsConnectedQuery"}
    actual = criteria[0].get("type", "")
    if actual not in valid_types:
        return CheckResult("connectivityCriteria type valid", False,
                           f"'{actual}' not in {sorted(valid_types)}")
    return CheckResult("connectivityCriteria type valid", True, f"type={actual}")


def check_pagination_no_duplicate_limit(template):
    """Check 12: limit/pageSize not duplicated in queryParameters AND pagination config."""
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    for nt in nested:
        mt = nt["mainTemplate"]
        for res in mt.get("resources", []):
            if res.get("kind") == "RestApiPoller":
                props = res.get("properties", {})
                paging = props.get("paging", {})
                request = props.get("request", {})
                query_params = request.get("queryParameters", {})

                page_size_param = paging.get("pageSizeParaName",
                                  paging.get("PageSizeParameterName",
                                  paging.get("pageSizeParameterName", "")))
                if page_size_param and page_size_param in query_params:
                    name = res.get("name", "unknown")
                    issues.append(
                        f"Connection '{name}': '{page_size_param}' in both "
                        "queryParameters and pagination config")

    if issues:
        return CheckResult("No duplicate pageSize params", False, "; ".join(issues))
    return CheckResult("No duplicate pageSize params", True)


def check_rate_limit_and_retry(template):
    """Check 13: rateLimitQPS and retryCount recommended on all pollers.

    Uses case-insensitive key lookup. Warning only  -- the platform has defaults
    and many production connectors omit these properties.
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    for nt in nested:
        mt = nt["mainTemplate"]
        for res in mt.get("resources", []):
            if res.get("kind") == "RestApiPoller":
                request = res.get("properties", {}).get("request", {})
                name = res.get("name", "unknown")
                short = name.split("/")[-1].strip("']")

                request_lower_keys = {k.lower() for k in request.keys()}
                has_rate = "ratelimitqps" in request_lower_keys
                has_retry = "retrycount" in request_lower_keys

                if not has_rate:
                    issues.append(f"'{short}': missing rateLimitQPS")
                if not has_retry:
                    issues.append(f"'{short}': missing retryCount")

    if issues:
        return CheckResult("Rate limit and retry configured", True,
                           "; ".join(issues), warning=True)
    return CheckResult("Rate limit and retry configured", True)


def check_polling_intervals_staggered(template):
    """Check 14: Polling intervals differ across connections (if >1)."""
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    intervals = []

    for nt in nested:
        mt = nt["mainTemplate"]
        for res in mt.get("resources", []):
            if res.get("kind") == "RestApiPoller":
                request = res.get("properties", {}).get("request", {})
                qw = request.get("queryWindowInMin")
                if qw is not None:
                    intervals.append(qw)

    if len(intervals) <= 1:
        return CheckResult("Polling intervals staggered", True, "Single connection, N/A")
    if len(set(intervals)) == 1:
        return CheckResult("Polling intervals staggered", True,
                           f"All connections use {intervals[0]} min  -- consider staggering "
                           "to spread API load", warning=True)
    return CheckResult("Polling intervals staggered", True,
                        f"Intervals: {intervals}")


def check_output_streams(template):
    """Check 15: outputStream prefixes match destination type."""
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    for nt in nested:
        mt = nt["mainTemplate"]
        for res in mt.get("resources", []):
            if res.get("type", "").endswith("dataCollectionRules"):
                flows = res.get("properties", {}).get("dataFlows", [])
                for i, flow in enumerate(flows):
                    output = flow.get("outputStream", "")
                    if output.endswith("_CL") and not output.startswith("Custom-"):
                        issues.append(
                            f"dataFlow[{i}]: custom table outputStream '{output}' "
                            "should start with Custom-")
                    if not output.endswith("_CL") and output.startswith("Custom-"):
                        issues.append(
                            f"dataFlow[{i}]: outputStream '{output}' has Custom- prefix "
                            "but no _CL suffix")

    if issues:
        return CheckResult("outputStream prefixes correct", False, "; ".join(issues))
    return CheckResult("outputStream prefixes correct", True)


def check_standard_output_streams(template):
    """Check 25: Microsoft-* outputStreams match known standard table names."""
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    for nt in nested:
        mt = nt["mainTemplate"]
        for res in mt.get("resources", []):
            if res.get("type", "").endswith("dataCollectionRules"):
                flows = res.get("properties", {}).get("dataFlows", [])
                for i, flow in enumerate(flows):
                    output = flow.get("outputStream", "")
                    if output.startswith("Microsoft-") and output not in KNOWN_STANDARD_STREAMS:
                        issues.append(
                            f"dataFlow[{i}]: outputStream '{output}' starts with "
                            "Microsoft- but is not a known standard table (possible typo)")

    if issues:
        return CheckResult("Standard Microsoft-* streams valid", False, "; ".join(issues))
    return CheckResult("Standard Microsoft-* streams valid", True)


# ============================================================
# Deployment-breaking structural checks
# (lessons learned from DMARC connector deployment failures)
# ============================================================

def check_content_template_version_suffix(template):
    """Check 27: Content template resource names include a version suffix.

    Production CCF connectors (Jira, 1Password) append the version variable
    to content template resource names. The Sentinel Portal uses this naming
    convention to locate templates. Without the version suffix, clicking
    Connect fails with "content template $XxxDefinition not found".

    Expected pattern:
      concat(..., templateNameVar, versionVar)
    Bad pattern:
      concat(..., templateNameVar)   -- missing version
    """
    resources = template.get("resources", [])
    issues = []

    for r in resources:
        if not r.get("type", "").endswith("contentTemplates"):
            continue
        name = r.get("name", "")
        content_kind = r.get("properties", {}).get("contentKind", "unknown")

        # Content template names should be ARM concat expressions containing
        # both a template name variable and a version variable.
        # Look for 'version' (case-insensitive) anywhere in the name expression.
        if not name:
            continue
        name_lower = name.lower()
        has_version_ref = ("version" in name_lower)

        if not has_version_ref:
            issues.append(
                f"{content_kind}: content template name missing version suffix. "
                f"Production pattern: concat(..., templateName, versionVar). "
                f"67/109 (61%) production Azure-Sentinel connectors omit this "
                f"suffix and deploy successfully. The version may be embedded "
                f"inside the variable value.")

    if issues:
        return CheckResult("Content template names include version suffix", True,
                           "\n        ".join(issues), warning=True)
    return CheckResult("Content template names include version suffix", True)


def check_content_template_name_no_doubled_version(template):
    """Check 41: Content template name variables must not embed the version.

    The content template resource name is built as:
        concat(..., templateNameVar, versionVar)
    If templateNameVar itself already contains the version (e.g.
        concat(workspace, '-dc-', uniquestring(...), '-', versionVar)
    ), the deployed resource name will have the version doubled:
        workspace-dc-hash-1.0.41.0.4
    This causes "content template $ConnectorDefinition not found" at
    connect time because Sentinel cannot locate the template.

    Fix: remove the version from the template name variable so it only
    appears once (appended by the resource name expression).
    """
    variables = template.get("variables", {})
    issues = []

    # Collect all version variable names referenced by content template resources
    version_var_names = set()
    for key, val in variables.items():
        if key.lower().startswith("dataconnectorversion"):
            version_var_names.add(key)

    if not version_var_names:
        return CheckResult("Content template name no doubled version", True)

    # Check template name variables for embedded version references
    for key, val in variables.items():
        if not key.lower().startswith("dataconnectortemplatename"):
            continue
        if not isinstance(val, str):
            continue

        # Look for any version variable reference inside this template name variable
        for vvar in version_var_names:
            if vvar in val:
                # This template name variable embeds the version -- check if
                # a content template resource also appends the same version
                for r in template.get("resources", []):
                    if not r.get("type", "").endswith("contentTemplates"):
                        continue
                    rname = r.get("name", "")
                    # Both the template name var and the version var appear
                    # in the resource name expression => version is doubled
                    if key in rname and vvar in rname:
                        content_kind = r.get("properties", {}).get(
                            "contentKind", "unknown")
                        issues.append(
                            f"{content_kind}: variable '{key}' already "
                            f"embeds variables('{vvar}'), but the content "
                            f"template resource name also appends it. "
                            f"This doubles the version in the deployed name "
                            f"(e.g. 'ws-dc-hash-1.0.41.0.4'), causing "
                            f"'content template not found' at connect time. "
                            f"Fix: remove the version from the variable "
                            f"definition so it is only appended once in "
                            f"the resource name")

    if issues:
        return CheckResult("Content template name no doubled version", False,
                           "; ".join(issues))
    return CheckResult("Content template name no doubled version", True)


def check_parent_params_in_double_bracket(template):
    """Check 28: No parent-scope parameters inside [[double-bracket]] expressions.

    ARM resolves parent-scope parameters() calls inside [[escaped]] strings at
    deploy time, injecting bare (unquoted) values that create invalid ARM
    expressions at connect time.

    Example of the bug:
      Source template:  "[[concat(parameters('workspace'), '/...')]"
      ARM stores:       "[concat(la-test-feb26, '/...')]"
      Connect-time:     FAILS  -- "la-test-feb26" is not a valid ARM expression

    Parameters defined ONLY in the nested template (apiKey, dcrConfig, etc.)
    are NOT affected  -- only parameters whose names also exist in the parent
    template's parameters section.

    Fix: use single brackets [expr] for fields that should resolve at deploy
    time (name, location), or reference a nested-template-only parameter.
    """
    parent_params = set(template.get("parameters", {}).keys())
    if not parent_params:
        return CheckResult("No parent-scope params in [[ expressions", True,
                           "No parent parameters found")

    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    for nt in nested:
        if nt["kind"] != "ResourcesDataConnector":
            continue
        mt = nt["mainTemplate"]

        for path, val in json_deep_strings(mt):
            if not isinstance(val, str) or not val.startswith("[["):
                continue

            # Find all parameters('xxx') references in the [[ expression
            param_refs = re.findall(r"parameters\('([^']+)'\)", val)
            for param_name in param_refs:
                if param_name in parent_params:
                    short_path = path.split(".", 2)[-1] if path.count(".") > 1 else path
                    issues.append(
                        f"\"[[\" expression at {short_path} references parent-scope "
                        f"parameter '{param_name}'. ARM will substitute the raw value "
                        f"at deploy time, producing an invalid expression at connect "
                        f"time (e.g., concat(myWorkspace,...) instead of "
                        f"concat('myWorkspace',...)).\n"
                        f"        Fix: use single brackets [expr] so it fully resolves "
                        f"at deploy time, or rename the nested parameter to avoid "
                        f"colliding with the parent parameter name.")

    if issues:
        return CheckResult("No parent-scope params in [[ expressions", False,
                           "\n        ".join(issues[:5]))
    return CheckResult("No parent-scope params in [[ expressions", True)


def check_nested_variable_forwarding(template):
    """Check 29: Connection template variables forward parent values.

    Variables in the connections template (ResourcesDataConnector) that also
    exist in the parent template should use [variables('varName')] to forward
    the parent's value. ARM evaluates these at deploy time, storing the
    resolved literal.

    Hardcoding literals causes version/name drift  -- e.g., bumping the parent
    version from 1.0.4 to 1.0.5 has no effect if the nested template
    hardcodes '1.0.4'.
    """
    parent_vars = template.get("variables", {})
    if not parent_vars:
        return CheckResult("Nested template variable forwarding", True,
                           "No parent variables found")

    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    # Variable name patterns that should be forwarded from parent
    forwardable_patterns = {
        "_dataConnectorContentId", "dataConnectorVersion",
        "_solutionName", "_solutionId", "_solutionAuthor", "_solutionTier"
    }

    for nt in nested:
        if nt["kind"] != "ResourcesDataConnector":
            continue
        nested_vars = nt["mainTemplate"].get("variables", {})

        for var_name, var_val in nested_vars.items():
            # Check if this variable exists in parent AND matches a forwardable pattern
            if var_name not in parent_vars:
                continue
            is_forwardable = any(pat in var_name for pat in forwardable_patterns)
            if not is_forwardable:
                continue

            # Should use [variables('varName')] pattern
            expected = f"[variables('{var_name}')]"
            if isinstance(var_val, str) and var_val == expected:
                continue  # Correctly forwarded

            # Hardcoded literal instead of forwarded reference
            if isinstance(var_val, str) and not var_val.startswith("["):
                issues.append(
                    f"Variable '{var_name}' is hardcoded as \"{var_val}\" instead "
                    f"of forwarding from parent via \"{expected}\". Hardcoded values "
                    f"cause drift when parent values change (e.g., version bumps).")

    if issues:
        return CheckResult("Nested template variable forwarding", False,
                           "\n        ".join(issues[:5]))
    return CheckResult("Nested template variable forwarding", True)


def check_content_product_id_richness(template):
    """Check 30: contentProductId uses sufficiently unique hash inputs.

    Production connectors include solutionId + kind + contentId + version
    in the uniqueString() hash. Using only contentId risks collisions and
    may cause the Portal to confuse different content types or versions.

    Good:  uniqueString(concat(solutionId,'-','DataConnector','-',contentId,'-',version))
    Bad:   uniqueString(contentId)
    """
    resources = template.get("resources", [])
    issues = []

    for r in resources:
        if not r.get("type", "").endswith("contentTemplates"):
            continue
        props = r.get("properties", {})
        cpid = props.get("contentProductId", "")
        content_kind = props.get("contentKind", "unknown")

        if not cpid:
            issues.append(f"{content_kind}: missing contentProductId")
            continue

        if "uniqueString" not in cpid:
            continue

        # Rich pattern: uniqueString(concat(...)) with multiple variable inputs
        # Simple pattern: uniqueString(variables('singleVar'))
        has_concat_in_unique = "uniqueString(concat(" in cpid
        if not has_concat_in_unique:
            issues.append(
                f"{content_kind}: contentProductId uniqueString uses a simple "
                f"input. Production pattern: uniqueString(concat(solutionId, "
                f"'-', kind, '-', contentId, '-', version)) for proper uniqueness.")

    if issues:
        return CheckResult("contentProductId uses rich uniqueString", True,
                           "\n        ".join(issues), warning=True)
    return CheckResult("contentProductId uses rich uniqueString", True)


def check_dcr_endpoint_properties(template):
    """Check 31: DCR resources have kind and dataCollectionEndpointId.

    Production connectors (Jira, 1Password) include a 'kind' property on
    the DCR resource and a 'dataCollectionEndpointId' in its properties.
    Missing these may cause issues with data collection endpoint routing.
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    for nt in nested:
        mt = nt["mainTemplate"]
        for res in mt.get("resources", []):
            if not res.get("type", "").endswith("dataCollectionRules"):
                continue

            if "kind" not in res:
                issues.append(
                    "DCR resource missing 'kind' property  -- add '\"kind\": \"\"' "
                    "at the resource level (same level as 'type' and 'properties')")

            props = res.get("properties", {})
            if "dataCollectionEndpointId" not in props:
                issues.append(
                    "DCR missing properties.dataCollectionEndpointId. Fix: "
                    "(1) Add a variable in the OUTER template: "
                    "\"dataCollectionEndpointId\": \"[concat('/subscriptions/',"
                    "parameters('subscription'),'/resourceGroups/',"
                    "parameters('resourceGroupName'),'/providers/"
                    "Microsoft.Insights/dataCollectionEndpoints/',"
                    "parameters('workspace'))]\"  -- "
                    "(2) Reference it in the DCR properties with SINGLE brackets: "
                    "\"dataCollectionEndpointId\": \"[variables("
                    "'dataCollectionEndpointId')]\"  -- "
                    "Do NOT use [[double brackets]] here; the DCE ID must resolve "
                    "at ARM deploy time, not connect time. "
                    "Do NOT use subscription()/resourceGroup() functions; use "
                    "parameters('subscription') and parameters('resourceGroupName').")
            else:
                # Validate bracket escaping on the value
                dce_val = props["dataCollectionEndpointId"]
                if isinstance(dce_val, str) and dce_val.startswith("[["):
                    issues.append(
                        "DCR properties.dataCollectionEndpointId uses [[double "
                        "brackets]] but this value must resolve at ARM deploy time. "
                        "Use single brackets: \"[variables('dataCollectionEndpointId')]\" "
                        "not \"[[variables('dataCollectionEndpointId')]]\"")

    if issues:
        return CheckResult("DCR has endpoint properties", False,
                           "; ".join(issues))
    return CheckResult("DCR has endpoint properties", True)


def check_connections_resource_ordering(template):
    """Check 32: Metadata comes before connector in connections template.

    Both Jira and 1Password production connectors place the metadata resource
    FIRST in the connections template's mainTemplate.resources[], before the
    connector resource. This matches the Portal's expected resource ordering.
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    for nt in nested:
        if nt["kind"] != "ResourcesDataConnector":
            continue
        mt_resources = nt["mainTemplate"].get("resources", [])

        metadata_idx = None
        connector_idx = None
        for i, res in enumerate(mt_resources):
            res_type = res.get("type", "")
            if res_type.endswith("/metadata"):
                if metadata_idx is None:
                    metadata_idx = i
            elif res.get("kind") and res.get("kind", "").lower() in VALID_CONNECTOR_KINDS:
                if connector_idx is None:
                    connector_idx = i

        if metadata_idx is not None and connector_idx is not None:
            if metadata_idx > connector_idx:
                issues.append(
                    f"Metadata resource (index {metadata_idx}) should come before "
                    f"connector resource (index {connector_idx}). Production "
                    f"connectors place metadata first in the resources array.")

    if issues:
        return CheckResult("Connections template resource ordering", False,
                           "; ".join(issues))
    return CheckResult("Connections template resource ordering", True)


def check_connector_definition_name_hardcoded(template):
    """Check 33: connectorDefinitionName in connector is a literal, not a parameter ref.

    Production connectors (Jira: 'JiraAuditCCPDefinition', 1Password:
    '1PasswordCCPDefinition') hardcode the connectorDefinitionName as a
    literal string. Using [[parameters('connectorDefinitionName')]] can cause
    resolution issues at connect time if the Portal doesn't pass the parameter.
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    for nt in nested:
        if nt["kind"] != "ResourcesDataConnector":
            continue
        for res in nt["mainTemplate"].get("resources", []):
            res_kind = res.get("kind", "")
            if not res_kind or res_kind.lower() not in VALID_CONNECTOR_KINDS:
                continue

            def_name = res.get("properties", {}).get("connectorDefinitionName", "")
            if def_name.startswith("[["):
                issues.append(
                    f"connectorDefinitionName is '{def_name}'  -- production "
                    f"connectors hardcode this as a literal string (e.g., "
                    f"'MyConnectorDefinition'), not a parameter reference.")

    if issues:
        return CheckResult("connectorDefinitionName is hardcoded", False,
                           "; ".join(issues))
    return CheckResult("connectorDefinitionName is hardcoded", True)


# ============================================================
# Cross-resource consistency checks
# (inspired by get-ccp-details.ps1 packaging validation)
# ============================================================

def check_poller_definition_mapping(template):
    """Check 16: Connector connectorDefinitionName matches definition connectorUiConfig.id.

    Works for all connector kinds (RestApiPoller, Push, WebSocket, etc.).
    Resolves ARM variable references from both nested and parent template scopes.
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    parent_vars = template.get("variables", {})

    # Collect definition IDs from top-level dataConnectorDefinitions
    defs = find_resources_by_type(resources,
        "Microsoft.OperationalInsights/workspaces/providers/dataConnectorDefinitions")
    definition_ids = set()
    for d in defs:
        ui_id = d.get("properties", {}).get("connectorUiConfig", {}).get("id", "")
        if ui_id:
            # Try resolving ARM variable reference from parent scope
            resolved = resolve_arm_variable(ui_id, template) if ui_id.startswith("[") else ui_id
            definition_ids.add(resolved or ui_id)

    # Also collect from nested DataConnector templates (the definition inside contentTemplates)
    for nt in nested:
        if nt["kind"] == "DataConnector":
            for res in nt["mainTemplate"].get("resources", []):
                if res.get("type", "").endswith("dataConnectorDefinitions"):
                    ui_id = res.get("properties", {}).get("connectorUiConfig", {}).get("id", "")
                    if ui_id:
                        resolved = resolve_arm_variable(ui_id, template) if ui_id.startswith("[") else ui_id
                        definition_ids.add(resolved or ui_id)

    if not definition_ids:
        return CheckResult("Connector-to-definition mapping", False,
                           "No connectorUiConfig.id found in any definition")

    # Check connector resources (any kind) reference a known definition ID
    issues = []
    connector_found = False
    for nt in nested:
        if nt["kind"] == "ResourcesDataConnector":
            for res in nt["mainTemplate"].get("resources", []):
                res_kind = res.get("kind", "")
                if not res_kind or res_kind.lower() not in VALID_CONNECTOR_KINDS:
                    continue
                connector_found = True
                def_name = res.get("properties", {}).get("connectorDefinitionName", "")

                # Try to resolve the definition name through multiple strategies
                resolved = def_name

                if def_name.startswith("[["):
                    # Strategy 1: Look up [[parameters('connectorDefinitionName')]
                    param_match = re.match(r"\[\[parameters\('([^']+)'\)\]", def_name)
                    if param_match:
                        param_name = param_match.group(1)
                        nested_params = nt["mainTemplate"].get("parameters", {})
                        default = nested_params.get(param_name, {}).get("defaultValue", "")
                        if default and not default.startswith("["):
                            resolved = default
                        elif default and default.startswith("["):
                            resolved_from_parent = resolve_arm_variable(default, template)
                            if resolved_from_parent:
                                resolved = resolved_from_parent

                    # Strategy 2: Look up nested template variables
                    if resolved == def_name:
                        nested_vars = nt["mainTemplate"].get("variables", {})
                        for var_name, var_val in nested_vars.items():
                            if "connectorDefinition" in var_name.lower() and isinstance(var_val, str):
                                if not var_val.startswith("["):
                                    resolved = var_val
                                else:
                                    r = resolve_arm_variable(var_val, template)
                                    if r:
                                        resolved = r
                                break

                elif def_name.startswith("[") and not def_name.startswith("[["):
                    # Single bracket  -- resolved at deploy time from parent scope
                    resolved_from_parent = resolve_arm_variable(def_name, template)
                    if resolved_from_parent:
                        resolved = resolved_from_parent

                # Compare resolved name against known definition IDs
                if resolved and not resolved.startswith("[") and resolved not in definition_ids:
                    issues.append(
                        f"Connector connectorDefinitionName '{resolved}' "
                        f"not found in definitions: {definition_ids}")

    if not connector_found:
        return CheckResult("Connector-to-definition mapping", False,
                           "No connector resource with recognized kind found")
    if issues:
        return CheckResult("Connector-to-definition mapping", False, "; ".join(issues))
    return CheckResult("Connector-to-definition mapping", True)


def check_poller_dcr_stream_consistency(template):
    """Check 17: Poller dcrConfig.streamName matches a DCR dataFlows.streams[] entry."""
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)

    # Collect all DCR stream names from the DataConnector contentTemplate
    dcr_streams = set()
    for nt in nested:
        if nt["kind"] == "DataConnector":
            for res in nt["mainTemplate"].get("resources", []):
                if res.get("type", "").endswith("dataCollectionRules"):
                    for flow in res.get("properties", {}).get("dataFlows", []):
                        for s in flow.get("streams", []):
                            dcr_streams.add(s)

    if not dcr_streams:
        return CheckResult("Poller-to-DCR stream consistency", False,
                           "No DCR dataFlow streams found")

    # Check poller streamName against DCR streams
    issues = []
    for nt in nested:
        if nt["kind"] == "ResourcesDataConnector":
            for res in nt["mainTemplate"].get("resources", []):
                if res.get("kind") == "RestApiPoller":
                    stream = res.get("properties", {}).get("dcrConfig", {}).get("streamName", "")
                    if stream and stream not in dcr_streams:
                        # Platform-managed connectors use logical stream names
                        # (e.g. SENTINEL_CROWDSTRIKEALERTS, ILUMIO_INSIGHTS) that
                        # map internally to Microsoft-* standard streams. These are
                        # all-uppercase with underscores. Skip them -- the platform
                        # handles the routing.
                        if stream.isupper() and stream.replace("_", "").isalpha():
                            continue
                        name = res.get("name", "unknown")
                        short = name.split("/")[-1].strip("']") if "/" in name else name
                        issues.append(
                            f"Poller '{short}' streamName '{stream}' "
                            f"not in DCR streams: {dcr_streams}")

    if issues:
        return CheckResult("Poller-to-DCR stream consistency", False, "; ".join(issues))
    return CheckResult("Poller-to-DCR stream consistency", True)


def check_dcr_output_table_consistency(template):
    """Check 18: DCR outputStream (minus Custom- prefix) matches a table resource name."""
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)

    # Collect table names from DataConnector contentTemplate
    table_names = set()
    for nt in nested:
        if nt["kind"] == "DataConnector":
            for res in nt["mainTemplate"].get("resources", []):
                if res.get("type", "").endswith("/tables"):
                    name = res.get("name", "")
                    resolved = resolve_arm_variable(name, template) if name.startswith("[") else name
                    if resolved:
                        table_names.add(resolved)
                    # Also check schema name as fallback
                    schema_name = res.get("properties", {}).get("schema", {}).get("name", "")
                    if schema_name:
                        table_names.add(schema_name)

    # Collect Custom- outputStreams from DCR
    issues = []
    for nt in nested:
        if nt["kind"] == "DataConnector":
            for res in nt["mainTemplate"].get("resources", []):
                if res.get("type", "").endswith("dataCollectionRules"):
                    for i, flow in enumerate(res.get("properties", {}).get("dataFlows", [])):
                        output = flow.get("outputStream", "")
                        if output.startswith("Custom-"):
                            expected_table = output.replace("Custom-", "", 1)
                            if table_names and expected_table not in table_names:
                                issues.append(
                                    f"dataFlow[{i}] outputStream '{output}' expects table "
                                    f"'{expected_table}', but found tables: {table_names}")
                        # Microsoft- prefixed outputs go to standard tables, no custom table needed

    if issues:
        return CheckResult("DCR outputStream-to-table mapping", False, "; ".join(issues))
    return CheckResult("DCR outputStream-to-table mapping", True)


def check_dcr_depends_on_tables(template):
    """Check 42: DCR has dependsOn for table resources it references.

    When a DCR's dataFlows reference Custom-* output streams, the corresponding
    tables must exist before the DCR is created. Without a dependsOn on the
    table resources, Azure may create the DCR first, causing:
      InvalidOutputTable: Table for output stream 'Custom-TableName_CL' is not
      available for destination 'clv2ws1'.

    This check verifies that the DCR resource has a dependsOn entry for each
    table resource whose name matches a Custom-* outputStream.
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    for nt in nested:
        if nt["kind"] != "DataConnector":
            continue
        mt_resources = nt["mainTemplate"].get("resources", [])

        # Collect table resource names (resolved or literal)
        table_res_names = set()
        for res in mt_resources:
            if not res.get("type", "").endswith("/tables"):
                continue
            name = res.get("name", "")
            resolved = resolve_arm_variable(name, template) if name.startswith("[") else name
            if resolved:
                # Strip workspace prefix if present (e.g. "ws/TableName" -> "TableName")
                table_res_names.add(resolved.split("/")[-1])
            # Also check schema name
            schema_name = res.get("properties", {}).get("schema", {}).get("name", "")
            if schema_name:
                table_res_names.add(schema_name.split("/")[-1])

        if not table_res_names:
            continue

        # Check each DCR for dependsOn coverage
        for res in mt_resources:
            if not res.get("type", "").endswith("dataCollectionRules"):
                continue

            depends_on = res.get("dependsOn", [])
            depends_str = " ".join(str(d) for d in depends_on).lower()

            # Find tables referenced by outputStreams
            for i, flow in enumerate(res.get("properties", {}).get("dataFlows", [])):
                output = flow.get("outputStream", "")
                if not output.startswith("Custom-"):
                    continue
                expected_table = output.replace("Custom-", "", 1)
                if expected_table not in table_res_names:
                    continue  # Mismatch caught by check 18

                # Check if the table appears in dependsOn
                if expected_table.lower() not in depends_str:
                    dcr_name = res.get("name", "DCR")
                    issues.append(
                        f"DCR '{dcr_name}' references output table "
                        f"'{expected_table}' but has no dependsOn for it. "
                        f"Without this dependency, the table may not exist "
                        f"when the DCR is created, causing "
                        f"InvalidOutputTable at connect time. "
                        f"Fix: add dependsOn entries for each table "
                        f"resource in the same nested template")

    if issues:
        return CheckResult("DCR dependsOn output tables", True,
                           "; ".join(issues), warning=True)
    return CheckResult("DCR dependsOn output tables", True)


# ============================================================
# Deep structural checks (ported from createCCPConnector.ps1)
# ============================================================

def check_poller_required_properties(template):
    """Check 19: RestApiPoller resources have all required properties."""
    pollers = find_poller_resources(template)
    if not pollers:
        return CheckResult("Poller required properties", True, "No poller resources found")

    issues = []
    warnings = []
    for res, _mt in pollers:
        kind = res.get("kind", "")
        if kind.lower() not in ("restapipoller", "websocket"):
            continue

        name = res.get("name", "unknown")
        short = name.split("/")[-1].strip("']") if "/" in name else name
        props = res.get("properties", {})

        # Required top-level properties
        _, cdn = get_prop_ci(props, "connectorDefinitionName")
        if cdn is None:
            issues.append(f"'{short}': missing properties.connectorDefinitionName")

        # dataType is optional  -- many production connectors omit it
        _, dt = get_prop_ci(props, "dataType")
        if dt is None:
            warnings.append(f"'{short}': missing properties.dataType (optional)")

        # dcrConfig
        _, dcr = get_prop_ci(props, "dcrConfig")
        if not isinstance(dcr, dict):
            issues.append(f"'{short}': missing or invalid properties.dcrConfig")
        else:
            _, sn = get_prop_ci(dcr, "streamName")
            if sn is None:
                issues.append(f"'{short}': missing dcrConfig.streamName")

        # auth
        _, auth = get_prop_ci(props, "auth")
        if not isinstance(auth, dict):
            issues.append(f"'{short}': missing or invalid properties.auth")
        else:
            if "type" not in auth:
                issues.append(f"'{short}': missing auth.type")

        # request
        _, req_obj = get_prop_ci(props, "request")
        if not isinstance(req_obj, dict):
            issues.append(f"'{short}': missing or invalid properties.request")

        # response with eventsJsonPaths (case-insensitive lookup)
        _, resp = get_prop_ci(props, "response")
        if not isinstance(resp, dict):
            issues.append(f"'{short}': missing or invalid properties.response")
        else:
            _, ejp = get_prop_ci(resp, "eventsJsonPaths")
            if not isinstance(ejp, list) or len(ejp) == 0:
                issues.append(f"'{short}': missing or empty response.eventsJsonPaths")

    if issues:
        return CheckResult("Poller required properties", False, "; ".join(issues))
    if warnings:
        return CheckResult("Poller required properties", True,
                           "; ".join(warnings), warning=True)
    return CheckResult("Poller required properties", True)


def check_auth_type_and_fields(template):
    """Check 20: auth.type is valid and has required fields per type."""
    pollers = find_poller_resources(template)
    if not pollers:
        return CheckResult("Auth type and required fields", True, "No poller resources found")

    valid_auth_types = {"oauth2", "basic", "apikey", "jwttoken", "alicloudslsv1"}
    issues = []
    warnings = []

    for res, _mt in pollers:
        kind = res.get("kind", "")
        if kind.lower() not in ("restapipoller", "websocket"):
            continue

        name = res.get("name", "unknown")
        short = name.split("/")[-1].strip("']") if "/" in name else name
        auth = res.get("properties", {}).get("auth", {})
        if not isinstance(auth, dict):
            continue  # Already caught by check 19

        auth_type = auth.get("type", "")
        if not auth_type:
            continue  # Already caught by check 19

        auth_type_lower = auth_type.lower()
        if auth_type_lower not in valid_auth_types:
            warnings.append(
                f"'{short}': auth.type '{auth_type}' not in known types "
                f"(OAuth2, Basic, APIKey, JwtToken, AliCloudSlsV1)  -- "
                "may be a vendor-specific extension")
            continue

        if auth_type_lower == "oauth2":
            _, cid = get_prop_ci(auth, "ClientId")
            _, csec = get_prop_ci(auth, "ClientSecret")
            if cid is None:
                issues.append(f"'{short}': OAuth2 auth missing ClientId")
            if csec is None:
                issues.append(f"'{short}': OAuth2 auth missing ClientSecret")
            _, gt = get_prop_ci(auth, "grantType")
            if isinstance(gt, str) and gt.lower() == "authorization_code":
                _, ac = get_prop_ci(auth, "AuthorizationCode")
                if ac is None:
                    issues.append(
                        f"'{short}': OAuth2 authorization_code grant missing AuthorizationCode")

        elif auth_type_lower == "basic":
            _, uname = get_prop_ci(auth, "UserName")
            _, pwd = get_prop_ci(auth, "Password")
            if uname is None:
                issues.append(f"'{short}': Basic auth missing UserName")
            if pwd is None:
                issues.append(f"'{short}': Basic auth missing Password")

        elif auth_type_lower == "apikey":
            _, akey = get_prop_ci(auth, "ApiKey")
            if akey is None:
                issues.append(f"'{short}': APIKey auth missing ApiKey")

        elif auth_type_lower == "jwttoken":
            _, uname = get_prop_ci(auth, "userName")
            _, pwd = get_prop_ci(auth, "password")
            _, utoken = get_prop_ci(auth, "UserToken")
            has_creds = uname is not None and pwd is not None
            has_token = utoken is not None
            if not has_creds and not has_token:
                issues.append(
                    f"'{short}': JwtToken auth requires either "
                    "(userName + password) or UserToken")
            _, te = get_prop_ci(auth, "TokenEndpoint")
            if te is None:
                issues.append(f"'{short}': JwtToken auth missing TokenEndpoint")

    if issues:
        return CheckResult("Auth type and required fields", False, "; ".join(issues))
    if warnings:
        return CheckResult("Auth type and required fields", True,
                           "; ".join(warnings), warning=True)
    return CheckResult("Auth type and required fields", True)


def check_poller_kind_allowlist(template):
    """Check 21: Connector resource kind is in the allowed set."""
    pollers = find_poller_resources(template)
    if not pollers:
        return CheckResult("Connector kind allowlist", True, "No poller resources found")

    issues = []
    for res, _mt in pollers:
        kind = res.get("kind", "")
        if kind.lower() not in VALID_CONNECTOR_KINDS:
            name = res.get("name", "unknown")
            short = name.split("/")[-1].strip("']") if "/" in name else name
            issues.append(
                f"'{short}': kind '{kind}' not in allowed set "
                f"{sorted(VALID_CONNECTOR_KINDS)}")

    if issues:
        return CheckResult("Connector kind allowlist", False, "; ".join(issues))
    return CheckResult("Connector kind allowlist", True)


def check_dcr_required_structure(template):
    """Check 22: DCR resources have required destinations, streamDeclarations, dataFlows."""
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []
    warnings = []

    for nt in nested:
        mt = nt["mainTemplate"]
        for res in mt.get("resources", []):
            if not res.get("type", "").endswith("dataCollectionRules"):
                continue
            props = res.get("properties", {})

            # destinations.logAnalytics
            destinations = props.get("destinations", {})
            la = destinations.get("logAnalytics")
            if not isinstance(la, list) or len(la) == 0:
                issues.append("DCR missing destinations.logAnalytics array")
            else:
                for i, entry in enumerate(la):
                    if "workspaceResourceId" not in entry:
                        issues.append(
                            f"DCR logAnalytics[{i}] missing workspaceResourceId")
                    else:
                        ws_val = entry["workspaceResourceId"]
                        if isinstance(ws_val, str) and ws_val.startswith("[["):
                            issues.append(
                                f"DCR logAnalytics[{i}].workspaceResourceId uses "
                                f"[[double brackets]] but must resolve at ARM deploy time "
                                f"(the DCR needs a real /subscriptions/... path). "
                                f"Use single brackets: "
                                f"\"[variables('workspaceResourceId')]\" not "
                                f"\"[[variables('workspaceResourceId')]]\". "
                                f"Double brackets here cause a LinkedInvalidPropertyId "
                                f"deployment error.")
                    if "name" not in entry:
                        issues.append(f"DCR logAnalytics[{i}] missing name")

            # streamDeclarations (some packager outputs omit this; warn, don't fail)
            sd = props.get("streamDeclarations")
            if not isinstance(sd, dict) or len(sd) == 0:
                warnings.append("DCR missing or empty streamDeclarations (may be inferred at deploy time)")

            # dataFlows
            flows = props.get("dataFlows")
            if not isinstance(flows, list) or len(flows) == 0:
                issues.append("DCR missing or empty dataFlows array")
            else:
                for i, flow in enumerate(flows):
                    # streams and destinations are always required
                    for req in ("streams", "destinations"):
                        if req not in flow:
                            issues.append(f"DCR dataFlow[{i}] missing {req}")

                    # transformKql and outputStream: required for Custom-* streams,
                    # optional for platform-managed (Microsoft-*) flows
                    if _is_platform_managed_flow(flow):
                        has_transform = "transformKql" in flow
                        has_output = "outputStream" in flow
                        if has_transform != has_output:
                            warnings.append(
                                f"DCR dataFlow[{i}] has "
                                f"{'transformKql' if has_transform else 'outputStream'} "
                                f"but not "
                                f"{'outputStream' if has_transform else 'transformKql'} "
                                f"(platform-managed Microsoft-* flow  -- partial presence "
                                f"is unusual)")
                        # Both missing is fine for platform-managed flows  -- skip silently
                    else:
                        for req in ("transformKql", "outputStream"):
                            if req not in flow:
                                issues.append(f"DCR dataFlow[{i}] missing {req}")

    if issues:
        return CheckResult("DCR required structure", False, "; ".join(issues))
    if warnings:
        return CheckResult("DCR required structure", True,
                           "; ".join(warnings), warning=True)
    return CheckResult("DCR required structure", True)


def check_dcr_name_length(template):
    """Check 40: DCR resource name must not exceed 64 characters.

    Azure enforces a 64-character limit on Data Collection Rule names.
    Since DCR names are typically built with concat('Prefix-', parameters('workspace')),
    we estimate the static prefix length and warn if the prefix is so long that
    a typical workspace name would breach the limit.
    """
    MAX_DCR_NAME_LEN = 64
    # Workspace names up to 63 chars are allowed by Azure; warn if even a
    # moderate-length workspace (40 chars) would push the name over the limit.
    WORKSPACE_BUDGET_WARN = 40

    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []
    warnings = []

    for nt in nested:
        mt = nt["mainTemplate"]
        for res in mt.get("resources", []):
            if not res.get("type", "").endswith("dataCollectionRules"):
                continue
            name = res.get("name", "")

            # Case 1: plain string (no ARM expression) -- check directly
            if not name.startswith("["):
                if len(name) > MAX_DCR_NAME_LEN:
                    issues.append(
                        f"DCR name '{name}' is {len(name)} chars, "
                        f"exceeding the {MAX_DCR_NAME_LEN}-char Azure limit")
                continue

            # Case 2: ARM concat expression -- extract static prefix length
            # Pattern: [concat('SomeDCR-', parameters('workspace'))]
            m = re.match(
                r"^\[concat\('([^']*)',\s*parameters\('([^']+)'\)\)\]$",
                name)
            if m:
                prefix = m.group(1)
                param_name = m.group(2)
                remaining = MAX_DCR_NAME_LEN - len(prefix)
                if remaining < WORKSPACE_BUDGET_WARN:
                    issues.append(
                        f"DCR name prefix '{prefix}' is {len(prefix)} chars, "
                        f"leaving only {remaining} chars for "
                        f"parameters('{param_name}'). "
                        f"Azure workspace names can be up to 63 chars; "
                        f"names over {MAX_DCR_NAME_LEN} chars will fail "
                        f"deployment with InvalidPayload. "
                        f"Shorten the prefix (e.g. abbreviate the vendor name)")
                elif remaining < 63:
                    warnings.append(
                        f"DCR name prefix '{prefix}' ({len(prefix)} chars) "
                        f"leaves {remaining} chars for "
                        f"parameters('{param_name}'). Workspace names up to "
                        f"63 chars are valid; very long names could breach "
                        f"the {MAX_DCR_NAME_LEN}-char limit")

    if issues:
        return CheckResult("DCR name length", False, "; ".join(issues))
    if warnings:
        return CheckResult("DCR name length", True,
                           "; ".join(warnings), warning=True)
    return CheckResult("DCR name length", True)


def check_definition_ui_config(template):
    """Check 23: dataConnectorDefinitions has required UI config properties."""
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []
    warnings = []

    # Check definitions inside DataConnector nested templates
    for nt in nested:
        if nt["kind"] != "DataConnector":
            continue
        for res in nt["mainTemplate"].get("resources", []):
            if not res.get("type", "").endswith("dataConnectorDefinitions"):
                continue
            ui = res.get("properties", {}).get("connectorUiConfig", {})
            if not ui:
                issues.append("Definition missing properties.connectorUiConfig")
                continue

            if not ui.get("id"):
                issues.append("Definition missing connectorUiConfig.id")
            if not ui.get("title"):
                issues.append("Definition missing connectorUiConfig.title")

            steps = ui.get("instructionSteps")
            if not isinstance(steps, list) or len(steps) == 0:
                issues.append("Definition missing connectorUiConfig.instructionSteps")
            else:
                # Check for toggle/deploy button or DataConnectorsContextPane
                all_types = collect_instruction_types(steps)
                type_names = {t for t, _p in all_types}
                has_toggle = "ConnectionToggleButton" in type_names
                has_push = "DeployPushConnectorButton" in type_names
                # ContextPane with DataConnectorsContextPane acts as connect mechanism
                has_context_pane = any(
                    t == "ContextPane" and
                    p.get("contextPaneType") == "DataConnectorsContextPane"
                    for t, p in all_types
                )
                # GCP connectors use GCPGrid / GCPContextPane
                has_gcp_grid = "GCPGrid" in type_names
                has_gcp_context_pane = any(
                    t == "ContextPane" and
                    p.get("contextPaneType") == "GCPContextPane"
                    for t, p in all_types
                )
                # Environment-based markdown control
                has_env_based = "MarkdownControlEnvBased" in type_names

                has_any_mechanism = (has_toggle or has_push or has_context_pane
                                     or has_gcp_grid or has_gcp_context_pane
                                     or has_env_based)
                if not has_any_mechanism:
                    found_types = sorted(type_names) if type_names else ["(none)"]
                    warnings.append(
                        "Definition instructionSteps has no recognized connect "
                        f"mechanism. Found types: {', '.join(found_types)}. "
                        "32/109 (29%) production connectors use non-standard "
                        "connect mechanisms and deploy successfully.")

    if issues:
        return CheckResult("Definition UI config required properties", False,
                           "; ".join(issues))
    if warnings:
        return CheckResult("Definition UI config required properties", True,
                           "; ".join(warnings), warning=True)
    return CheckResult("Definition UI config required properties", True)


def check_instruction_parameters_match(template):
    """Check 24: UI instruction parameters match connections template parameters."""
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)

    # Collect connection template parameters (from ResourcesDataConnector)
    conn_params = set()
    for nt in nested:
        if nt["kind"] == "ResourcesDataConnector":
            for pname in nt["mainTemplate"].get("parameters", {}).keys():
                conn_params.add(pname)

    if not conn_params:
        return CheckResult("Instruction params match connection template", True,
                           "No connection template parameters found")

    # Collect expected parameter names from definition instruction steps
    expected_params = set()
    for nt in nested:
        if nt["kind"] != "DataConnector":
            continue
        for res in nt["mainTemplate"].get("resources", []):
            if not res.get("type", "").endswith("dataConnectorDefinitions"):
                continue
            steps = (res.get("properties", {})
                     .get("connectorUiConfig", {})
                     .get("instructionSteps", []))
            all_instrs = collect_instruction_types(steps)
            for itype, params in all_instrs:
                if itype == "Textbox":
                    name = params.get("name", "")
                    if name:
                        expected_params.add(name)
                elif itype == "OAuthForm":
                    expected_params.add("ClientId")
                    expected_params.add("ClientSecret")
                    expected_params.add("AuthorizationCode")
                elif itype == "Dropdown":
                    name = params.get("name", "")
                    if name:
                        expected_params.add(name)

    if not expected_params:
        return CheckResult("Instruction params match connection template", True,
                           "No UI instruction parameters found")

    # Check which expected params are missing from connection template
    # ARM parameter names are case-insensitive, so compare accordingly
    conn_params_lower = {p.lower() for p in conn_params}
    missing = {p for p in expected_params if p.lower() not in conn_params_lower}
    if missing:
        return CheckResult("Instruction params match connection template", False,
                           f"UI parameters not in connection template: {sorted(missing)}")
    return CheckResult("Instruction params match connection template", True,
                        f"All {len(expected_params)} UI params matched")


# ============================================================
# Naming convention checks
# ============================================================

# Known packager-generated variable names that use 'CCP'  --
# these are auto-generated by Microsoft's solution packager and
# connector authors don't control them.
_PACKAGER_CCP_VARIABLES = {"dataconnectorccpversion"}


def _find_ccp_in_json(obj, path=""):
    """Recursively find dict keys and string values containing 'ccp' (case-insensitive)."""
    hits = []
    if isinstance(obj, str):
        if "ccp" in obj.lower():
            hits.append(("value", path, obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            child_path = f"{path}.{k}" if path else k
            if "ccp" in k.lower():
                hits.append(("key", child_path, k))
            hits.extend(_find_ccp_in_json(v, child_path))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(_find_ccp_in_json(v, f"{path}[{i}]"))
    return hits


def _is_packager_ccp_hit(kind, json_path, raw):
    """Check if a CCP naming hit is from a known packager-generated artifact."""
    # Skip $schema URLs  -- out of our control
    if "$schema" in json_path:
        return True
    # Skip known packager-generated variable names (e.g., dataConnectorCCPVersion)
    if kind == "key" and raw.lower() in _PACKAGER_CCP_VARIABLES:
        return True
    # Skip values that reference packager variables (ARM expressions like
    # "[variables('dataConnectorCCPVersion')]" or concat expressions containing them)
    if kind == "value" and isinstance(raw, str):
        raw_lower = raw.lower()
        if any(pv in raw_lower for pv in _PACKAGER_CCP_VARIABLES):
            return True
    return False


def check_no_ccp_naming(template, path):
    """Check 26: Files and identifiers use 'ccf', not legacy 'ccp' naming.

    Microsoft renamed CCP (Codeless Connector Platform) to CCF (Codeless
    Connector Framework) in June 2025. Connectors created before that date
    legitimately use 'CCP' in their identifiers and cannot easily change
    published resource IDs. This check warns on legacy naming but does not
    fail  -- only new connectors (created after June 2025) should use 'CCF'.

    Ref: https://devicebase.net/en/microsoft-sentinel/updates/codeless-connector-platform-ccp-has-been-renamed-to-codeless-connector-framework-ccf/6x9

    Excludes packager-generated artifacts like 'dataConnectorCCPVersion' which
    are auto-generated by Microsoft's solution packager tool.
    """
    issues = []

    # Check input file path
    if "ccp" in Path(path).name.lower():
        issues.append(f"File name contains 'ccp': {Path(path).name}")

    # Recursively scan all keys and string values in the template
    hits = _find_ccp_in_json(template)
    for kind, json_path, raw in hits:
        if _is_packager_ccp_hit(kind, json_path, raw):
            continue
        label = "Key" if kind == "key" else "Value"
        truncated = (raw[:80] + "...") if len(raw) > 80 else raw
        issues.append(f"{label} contains 'ccp' at {json_path}: {truncated}")

    if issues:
        detail = "; ".join(issues[:10])
        if len(issues) > 10:
            detail += f"; ... and {len(issues) - 10} more"
        detail += (". NOTE: 'CCP' naming is acceptable in connectors created "
                   "before June 2025 (pre-rebrand). New connectors must use 'CCF'.")
        return CheckResult("No legacy 'ccp' naming (use 'ccf')", True,
                           detail, warning=True)
    return CheckResult("No legacy 'ccp' naming (use 'ccf')", True)


# ============================================================
# Edge-case checks (Checks 34-36)
# ============================================================

_COLUMN_NAME_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_]*$')


def check_column_name_validity(template):
    """Check 34: Column names in tables and DCR streams follow Azure Monitor rules.

    Table columns: 2-45 chars, start with letter, letters/digits/underscores only,
    must not conflict with reserved names.
    Stream columns: same character rules, but reserved name check is skipped
    (KQL transforms rename them), and >45 chars is a warning not a failure.
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []
    warnings = []

    for nt in nested:
        mt = nt["mainTemplate"]
        for res in mt.get("resources", []):
            res_type = res.get("type", "")

            # --- Table columns ---
            if res_type.endswith("/tables"):
                columns = res.get("properties", {}).get("schema", {}).get("columns", [])
                for col in columns:
                    name = col.get("name", "")
                    if not name:
                        continue
                    if len(name) < 2:
                        issues.append(
                            f"Table column '{name}' length {len(name)} below "
                            f"minimum of 2")
                    if len(name) > 45:
                        # 3+ production connectors have >45 char columns and
                        # deploy successfully -- warn, don't fail
                        warnings.append(
                            f"Table column '{name}' length {len(name)} exceeds "
                            f"documented limit of 45 (may still deploy)")
                    if not _COLUMN_NAME_RE.match(name):
                        issues.append(
                            f"Table column '{name}' has invalid characters "
                            f"(must start with letter, then letters/digits/underscores)")
                    if name.lower() in RESERVED_TABLE_COLUMN_NAMES:
                        # 24/110 (22%) production connectors use reserved names
                        # like 'id' and 'TITLE' and deploy successfully
                        warnings.append(
                            f"Table column '{name}' conflicts with reserved name "
                            f"(24/110 production connectors use this pattern)")

            # --- DCR stream columns ---
            # Stream columns are input-side: they represent the raw API payload
            # shape. Character validity rules do NOT apply -- the KQL transform
            # renames columns before output. Only check length as a warning.
            if res_type.endswith("dataCollectionRules"):
                streams = res.get("properties", {}).get("streamDeclarations", {})
                for sname, sdef in streams.items():
                    for col in sdef.get("columns", []):
                        name = col.get("name", "")
                        if not name:
                            continue
                        if len(name) > 45:
                            warnings.append(
                                f"Stream '{sname}' column '{name}' is {len(name)} "
                                f"chars (>45; production DCRs allow up to ~60)")

    if issues:
        return CheckResult("Column name validity", False, "; ".join(issues))
    if warnings:
        return CheckResult("Column name validity", True,
                           "; ".join(warnings), warning=True)
    return CheckResult("Column name validity", True)


def check_time_generated_type(template):
    """Check 35: TimeGenerated columns in table resources are typed as datetime.

    A table with TimeGenerated typed as 'string' will deploy but produce
    broken ingestion.
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    for nt in nested:
        mt = nt["mainTemplate"]
        for res in mt.get("resources", []):
            if not res.get("type", "").endswith("/tables"):
                continue
            columns = res.get("properties", {}).get("schema", {}).get("columns", [])
            for col in columns:
                if col.get("name", "") == "TimeGenerated":
                    col_type = col.get("type", "")
                    if col_type.lower() != "datetime":
                        table_name = res.get("name", "unknown")
                        issues.append(
                            f"Table '{table_name}': TimeGenerated has type "
                            f"'{col_type}' (must be 'datetime')")

    if issues:
        return CheckResult("TimeGenerated column type is datetime", False,
                           "; ".join(issues))
    return CheckResult("TimeGenerated column type is datetime", True)


def check_time_filter_parameters(template):
    """Check 48: Time filter parameters use consistent naming and have both start/end.

    APIs vary in time filter format - some use bracket notation (created_at[gte]),
    others use double-underscore (created_at__gte). This check ensures:
    1. If startTimeAttributeName is set, endTimeAttributeName should also be set
    2. Both parameters use the same naming convention (both brackets or both underscores)
    
    Common patterns:
    - Bracket style: created_at[gte], created_at[lt] (used by Sublime audit log)
    - Underscore style: created_at__gte, created_at__lt (used by Sublime message groups)
    """
    pollers = find_poller_resources(template)
    if not pollers:
        return CheckResult("Time filter parameters consistent", True, "No poller resources found")

    issues = []
    for res, _mt in pollers:
        kind = res.get("kind", "")
        if kind.lower() not in ("restapipoller", "websocket"):
            continue

        name = res.get("name", "unknown")
        short = name.split("/")[-1].strip("']") if "/" in name else name
        request = res.get("properties", {}).get("request", {})
        
        start_param = request.get("startTimeAttributeName", "")
        end_param = request.get("endTimeAttributeName", "")
        
        # Check 1: If start is set but end is missing
        if start_param and not end_param:
            issues.append(
                f"'{short}': has startTimeAttributeName ('{start_param}') but "
                f"missing endTimeAttributeName. Without an end time, the API may "
                f"return unlimited historical data, causing duplicate ingestion.")
            continue
            
        # Check 2: If both are set, ensure consistent naming convention
        if start_param and end_param:
            # Detect naming convention
            start_has_brackets = "[" in start_param and "]" in start_param
            end_has_brackets = "[" in end_param and "]" in end_param
            start_has_underscore = "__" in start_param
            end_has_underscore = "__" in end_param
            
            # Mixed conventions are suspicious
            if start_has_brackets != end_has_brackets:
                issues.append(
                    f"'{short}': Mixed time filter naming conventions - "
                    f"start uses '{start_param}' ({'brackets' if start_has_brackets else 'underscores'}), "
                    f"end uses '{end_param}' ({'brackets' if end_has_brackets else 'underscores'}). "
                    f"Both should use the same convention.")
            
            # Check for common mistakes
            if "__gte" in start_param and "__lte" in end_param:
                issues.append(
                    f"'{short}': Using __lte (less than or equal) for end time "
                    f"with __gte (greater than or equal) for start time. "
                    f"This creates overlapping windows. Use __lt (less than) "
                    f"instead of __lte to avoid duplicates at boundaries.")

    if issues:
        return CheckResult("Time filter parameters consistent", False, "; ".join(issues))
    return CheckResult("Time filter parameters consistent", True)


def check_dcr_internal_stream_consistency(template):
    """Check 36: DCR dataFlows stream names exactly match streamDeclarations keys.

    A case mismatch (e.g., Custom-MyStream vs Custom-myStream) causes silent
    ingestion failure. Existing Check 17 validates poller->DCR consistency;
    this check catches mismatches *within* the DCR itself.
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    for nt in nested:
        mt = nt["mainTemplate"]
        for res in mt.get("resources", []):
            if not res.get("type", "").endswith("dataCollectionRules"):
                continue
            stream_decls = res.get("properties", {}).get("streamDeclarations", {})
            if not stream_decls:
                continue
            stream_decl_keys = set(stream_decls.keys())
            lower_map = {k.lower(): k for k in stream_decl_keys}

            for flow in res.get("properties", {}).get("dataFlows", []):
                for stream_name in flow.get("streams", []):
                    # Microsoft-* streams are platform-managed and do not need
                    # entries in streamDeclarations (e.g. Microsoft-ABAPAuditLog)
                    if stream_name.startswith("Microsoft-"):
                        continue
                    if stream_name in stream_decl_keys:
                        continue  # Exact match  -- OK
                    if stream_name.lower() in lower_map:
                        actual = lower_map[stream_name.lower()]
                        issues.append(
                            f"Case mismatch in DCR: dataFlows references "
                            f"'{stream_name}' but streamDeclarations has "
                            f"'{actual}'")
                    else:
                        issues.append(
                            f"Stream '{stream_name}' in dataFlows not found "
                            f"in streamDeclarations")

    if issues:
        return CheckResult("DCR internal stream consistency", False,
                           "; ".join(issues))
    return CheckResult("DCR internal stream consistency", True)


def check_no_redundant_ui_headings(template):
    """Check 37: Markdown instructions don't duplicate headings Sentinel renders.

    The Sentinel connector page automatically renders a 'Configuration' heading
    above the instructionSteps content. Including '## Configuration' in the
    Markdown creates a visible duplicate heading in the UI.
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    issues = []

    for nt in nested:
        if nt["kind"] != "DataConnector":
            continue
        for res in nt["mainTemplate"].get("resources", []):
            if not res.get("type", "").endswith("dataConnectorDefinitions"):
                continue
            ui = res.get("properties", {}).get("connectorUiConfig", {})
            steps = ui.get("instructionSteps")
            if not isinstance(steps, list):
                continue
            all_instructions = collect_instruction_types(steps)
            for itype, params in all_instructions:
                if itype != "Markdown":
                    continue
                content = params.get("content", "")
                if not isinstance(content, str):
                    continue
                for line in content.splitlines():
                    if re.match(r'^#{1,3}\s*Configuration\s*$', line):
                        issues.append(
                            f"Markdown instruction contains '{line.strip()}' but "
                            f"Sentinel automatically renders a 'Configuration' "
                            f"heading above instructionSteps content. This creates "
                            f"a visible duplicate heading in the UI. Fix: remove "
                            f"the '{line.strip()}' line from the Markdown content.")

    if issues:
        return CheckResult("No redundant UI headings", False,
                           "; ".join(issues))
    return CheckResult("No redundant UI headings", True)


def check_textbox_default_values(template):
    """Check 38: Textbox instructions with placeholder should have defaultValue.

    A Textbox with only a 'placeholder' shows grey hint text that the user must
    retype manually. If the placeholder represents a sensible default (e.g. a
    base URL), add 'defaultValue' so the field is pre-populated and the user
    only needs to change it if their value differs.
    """
    resources = template.get("resources", [])
    nested = find_nested_templates(resources)
    warnings = []

    for nt in nested:
        if nt["kind"] != "DataConnector":
            continue
        for res in nt["mainTemplate"].get("resources", []):
            if not res.get("type", "").endswith("dataConnectorDefinitions"):
                continue
            ui = res.get("properties", {}).get("connectorUiConfig", {})
            steps = ui.get("instructionSteps")
            if not isinstance(steps, list):
                continue
            all_instructions = collect_instruction_types(steps)
            for itype, params in all_instructions:
                if itype != "Textbox":
                    continue
                has_placeholder = "placeholder" in params
                has_default = "defaultValue" in params
                # Skip credential fields -- they should never have a default
                name_lower = params.get("name", "").lower()
                is_credential = any(kw in name_lower for kw in
                    {"apikey", "api_key", "password", "secret", "token",
                     "credential", "key"})
                if has_placeholder and not has_default and not is_credential:
                    label = params.get("label", "(unknown)")
                    name = params.get("name", "(unknown)")
                    warnings.append(
                        f"Textbox '{label}' (name='{name}') has a placeholder "
                        f"but no defaultValue. The placeholder only shows grey "
                        f"hint text that the user must retype manually. If the "
                        f"placeholder represents a sensible default (e.g. a base "
                        f"URL), add a 'defaultValue' so the field is pre-populated.")

    if warnings:
        return CheckResult("Textbox default values", True,
                           "; ".join(warnings), warning=True)
    return CheckResult("Textbox default values", True)


# ============================================================
# ARM TTK-equivalent checks (mainTemplate)
# ============================================================

def check_parameters_must_be_referenced(template):
    """Check A1: Every declared parameter must be referenced somewhere in the template.

    Mirrors the ARM TTK 'Parameters Must Be Referenced' check. Serializes the
    template to a string and searches for parameters('name') references.
    """
    params = template.get("parameters", {})
    if not params:
        return CheckResult("Parameters must be referenced", True, "No parameters declared")

    template_str = json.dumps(template)
    unreferenced = []
    for pname in params:
        # ARM function call: parameters('name')
        if f"parameters('{pname}')" not in template_str:
            unreferenced.append(pname)

    if unreferenced:
        return CheckResult("Parameters must be referenced", False,
                           f"Unreferenced parameters: {', '.join(unreferenced)}")
    return CheckResult("Parameters must be referenced", True)


def check_variables_must_be_referenced(template):
    """Check A2: Every declared variable must be referenced somewhere in the template.

    Mirrors the ARM TTK 'Variables Must Be Referenced' check.
    """
    variables = template.get("variables", {})
    if not variables:
        return CheckResult("Variables must be referenced", True, "No variables declared")

    template_str = json.dumps(template)
    unreferenced = []
    for vname in variables:
        # ARM function call: variables('name')
        if f"variables('{vname}')" not in template_str:
            unreferenced.append(vname)

    if unreferenced:
        return CheckResult("Variables must be referenced", False,
                           f"Unreferenced variables: {', '.join(unreferenced)}")
    return CheckResult("Variables must be referenced", True)


def check_template_should_not_contain_blanks(template):
    """Check A3: Template should not contain blank string values.

    Mirrors the ARM TTK 'Template Should Not Contain Blanks' check. Walks all
    properties looking for empty string values, skipping known-acceptable
    locations like parameter defaultValue and dcrConfig object defaults.
    """
    issues = []
    for path, value in json_deep_strings(template):
        if value != "":
            continue
        # Skip parameter defaultValue -- many are intentionally blank
        # e.g. .parameters.workspace.defaultValue = ""
        # This also covers nested template parameters like
        # .resources[6].properties.mainTemplate.parameters.apikey.defaultValue
        if ".defaultValue" in path and ".parameters." in path:
            continue
        # Skip dcrConfig defaults inside nested templates (deep paths)
        if "dcrConfig" in path and "defaultValue" in path:
            continue
        # Skip empty instructionSteps descriptions (common and harmless)
        if ".description" in path and "instructionSteps" in path:
            continue
        # Skip metadata description fields that may be intentionally empty
        if path.endswith(".description") and ".metadata." in path:
            continue
        issues.append(path)

    if issues:
        # Show at most 5 paths to keep output readable
        shown = issues[:5]
        suffix = f" (and {len(issues) - 5} more)" if len(issues) > 5 else ""
        return CheckResult("Template should not contain blanks", True,
                           f"Empty string values at: {', '.join(shown)}{suffix}. "
                           f"Blank values are common in CCF connectors (e.g. "
                           f"resource 'kind' fields). Review to confirm they are "
                           f"intentional.", warning=True)
    return CheckResult("Template should not contain blanks", True)


def check_secure_string_no_default(template):
    """Check A4: Securestring parameters must not have a non-empty default value.

    Mirrors the ARM TTK 'Secure String Parameters Cannot Have Default' check.
    Only checks top-level template parameters. Nested template parameters
    inside contentTemplates are excluded because Content Hub connectors
    universally use securestring defaults ("-NA-", ARM expressions, etc.)
    as placeholders -- these are never real secrets. 103/110 production
    connectors use this pattern.
    """
    issues = []

    # Check top-level parameters only (matching ARM TTK scope)
    for pname, pdef in template.get("parameters", {}).items():
        if pdef.get("type", "").lower() == "securestring":
            default = pdef.get("defaultValue", "")
            if default and str(default).strip():
                issues.append(f"Top-level parameter '{pname}'")

    if issues:
        return CheckResult("Secure string params cannot have default", False,
                           f"Securestring with non-empty defaultValue: {'; '.join(issues)}")
    return CheckResult("Secure string params cannot have default", True)


def check_deployment_template_schema(template):
    """Check A5: Top-level $schema must be the correct deploymentTemplate schema.

    Mirrors the ARM TTK 'DeploymentTemplate Schema Is Correct' check.
    """
    expected = "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#"
    actual = template.get("$schema", "")
    if actual != expected:
        return CheckResult("DeploymentTemplate schema is correct", False,
                           f"Expected '{expected}', got '{actual}'")
    return CheckResult("DeploymentTemplate schema is correct", True)


# ============================================================
# createUiDefinition.json checks
# ============================================================

def load_ui_definition(ui_path):
    """Load and parse a createUiDefinition.json file. Returns (data, error_msg)."""
    try:
        with open(ui_path, "r", encoding="utf-8") as f:
            return json.load(f), None
    except json.JSONDecodeError as e:
        return None, str(e)
    except OSError as e:
        return None, str(e)


def check_ui_definition_exists(ui_path):
    """Check B1: createUiDefinition.json exists and is valid JSON."""
    if not ui_path.exists():
        return CheckResult("createUiDefinition.json exists", True,
                           "File not found (skipping UI checks)", warning=True)
    data, err = load_ui_definition(ui_path)
    if err:
        return CheckResult("createUiDefinition.json valid JSON", False, err)
    return CheckResult("createUiDefinition.json valid JSON", True)


def check_ui_definition_schema(ui_data):
    """Check B2: createUiDefinition.json must have the correct $schema."""
    schema = ui_data.get("$schema", "")
    if "CreateUIDefinition.MultiVm.json" not in schema:
        return CheckResult("createUiDefinition has correct schema", False,
                           f"$schema should contain 'CreateUIDefinition.MultiVm.json', "
                           f"got '{schema}'")
    return CheckResult("createUiDefinition has correct schema", True)


def check_ui_definition_handler(ui_data):
    """Check B3: handler must be 'Microsoft.Azure.CreateUIDef'."""
    handler = ui_data.get("handler", "")
    if handler != "Microsoft.Azure.CreateUIDef":
        return CheckResult("createUiDefinition handler is correct", False,
                           f"Expected 'Microsoft.Azure.CreateUIDef', got '{handler}'")
    return CheckResult("createUiDefinition handler is correct", True)


def check_ui_definition_location_output(ui_data):
    """Check B4: parameters.outputs must contain a 'location' key."""
    outputs = ui_data.get("parameters", {}).get("outputs", {})
    if "location" not in outputs:
        return CheckResult("createUiDefinition outputs contain location", False,
                           "Missing 'location' in parameters.outputs -- "
                           "deployment will fail without location output")
    return CheckResult("createUiDefinition outputs contain location", True)


def check_ui_definition_outputs_match_parameters(ui_data, template):
    """Check B5: Each createUiDefinition output must match a mainTemplate parameter."""
    outputs = ui_data.get("parameters", {}).get("outputs", {})
    template_params = set(template.get("parameters", {}).keys())
    missing = []
    for key in outputs:
        if key not in template_params:
            missing.append(key)

    if missing:
        return CheckResult("createUiDefinition outputs match template parameters", False,
                           f"Outputs not in mainTemplate parameters: {', '.join(missing)}")
    return CheckResult("createUiDefinition outputs match template parameters", True)


def run_ui_definition_checks(ui_path, template):
    """Run all createUiDefinition.json checks. Returns list of CheckResult."""
    results = []

    # B1: exists and valid JSON
    result = check_ui_definition_exists(ui_path)
    results.append(result)
    if not result.passed or not ui_path.exists():
        # If file doesn't exist (warning) or invalid JSON (fail), skip rest
        return results

    ui_data, _ = load_ui_definition(ui_path)

    results.append(check_ui_definition_schema(ui_data))        # B2
    results.append(check_ui_definition_handler(ui_data))        # B3
    results.append(check_ui_definition_location_output(ui_data))  # B4
    results.append(check_ui_definition_outputs_match_parameters(ui_data, template))  # B5

    return results


# ============================================================
# Main runner
# ============================================================

def run_all_checks(path, connector_type="pull", verbose=False):
    """Run all validation checks and print results."""
    results = []

    # Check 0: JSON valid
    result = check_json_valid(path)
    results.append(result)
    if not result.passed:
        print_results(results)
        return results

    template = load_template(path)

    checks = [
        lambda: check_resource_count(template),                          # 1
        lambda: check_solution_version(template),                        # 2
        lambda: check_content_packages_properties(template),             # 3
        lambda: check_depends_on(template),                              # 4
        lambda: check_bracket_escaping(template),                        # 5
        lambda: check_parent_params_in_double_bracket(template),         # 28
        lambda: check_stream_declarations(template),                     # 6
        lambda: check_time_generated_type(template),                     # 35
        lambda: check_time_filter_parameters(template),                  # 48
        lambda: check_table_names(template),                             # 7
        lambda: check_column_name_validity(template),                    # 34
        lambda: check_kql_transforms(template),                          # 8
        lambda: check_securestring(template),                            # 9
        lambda: check_connector_kind(template),                          # 10
        lambda: check_connectivity_criteria(template, connector_type),   # 11
        lambda: check_pagination_no_duplicate_limit(template),           # 12
        lambda: check_rate_limit_and_retry(template),                    # 13
        lambda: check_polling_intervals_staggered(template),             # 14
        lambda: check_output_streams(template),                          # 15
        lambda: check_standard_output_streams(template),                 # 25 (after 15)
        lambda: check_content_template_version_suffix(template),         # 27
        lambda: check_content_template_name_no_doubled_version(template), # 41
        lambda: check_nested_variable_forwarding(template),              # 29
        lambda: check_content_product_id_richness(template),             # 30
        lambda: check_dcr_endpoint_properties(template),                 # 31
        lambda: check_connections_resource_ordering(template),           # 32
        lambda: check_connector_definition_name_hardcoded(template),     # 33
        lambda: check_poller_definition_mapping(template),               # 16
        lambda: check_poller_dcr_stream_consistency(template),           # 17
        lambda: check_dcr_internal_stream_consistency(template),         # 36
        lambda: check_dcr_output_table_consistency(template),            # 18
        lambda: check_dcr_depends_on_tables(template),                  # 42
        lambda: check_poller_required_properties(template),              # 19
        lambda: check_auth_type_and_fields(template),                    # 20
        lambda: check_poller_kind_allowlist(template),                   # 21
        lambda: check_dcr_required_structure(template),                  # 22
        lambda: check_dcr_name_length(template),                        # 40
        lambda: check_definition_ui_config(template),                    # 23
        lambda: check_instruction_parameters_match(template),            # 24
        lambda: check_no_ccp_naming(template, path),                     # 26
        lambda: check_no_redundant_ui_headings(template),               # 37
        lambda: check_textbox_default_values(template),                 # 38
        lambda: check_definition_template_depends_on(template),          # 43
        lambda: check_connections_content_product_id_prefix(template),   # 44
        lambda: check_connections_metadata_parent_id(template),          # 45
        lambda: check_nested_table_no_kind_or_location(template),        # 46
        lambda: check_top_level_tables_exist(template),                  # 47
        lambda: check_deploy_time_double_brackets(template),             # 39
        # ARM TTK-equivalent checks (Group A)
        lambda: check_parameters_must_be_referenced(template),           # A1
        lambda: check_variables_must_be_referenced(template),            # A2
        lambda: check_template_should_not_contain_blanks(template),      # A3
        lambda: check_secure_string_no_default(template),                # A4
        lambda: check_deployment_template_schema(template),              # A5
    ]

    for check in checks:
        results.append(check())

    # createUiDefinition.json checks (Group B) -- auto-discover from same directory
    ui_path = Path(path).parent / "createUiDefinition.json"
    results.extend(run_ui_definition_checks(ui_path, template))

    print_results(results, verbose)
    return results


def print_results(results, verbose=False):
    """Print formatted results."""
    passed = sum(1 for r in results if r.passed and not r.warning)
    warned = sum(1 for r in results if r.warning)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    print(f"\n{'='*60}")
    summary = f"  CCF Connector Validation: {passed}/{total} passed"
    if warned:
        summary += f", {warned} warning(s)"
    print(summary)
    print(f"{'='*60}\n")

    for r in results:
        if verbose or not r.passed or r.warning:
            print(r)
        elif r.passed:
            print(f"  PASS  {r.name}")

    print()
    if failed:
        print(f"  {failed} check(s) FAILED  -- fix before deploying.")
    elif warned:
        print(f"  All checks passed with {warned} informational warning(s) (no fixes required).")
    else:
        print(f"  All {total} checks passed.")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_connector.py <mainTemplate.json> [--verbose] [--connector-type pull|push]")
        sys.exit(1)

    path = sys.argv[1]
    verbose = "--verbose" in sys.argv
    connector_type = "pull"
    if "--connector-type" in sys.argv:
        idx = sys.argv.index("--connector-type")
        if idx + 1 < len(sys.argv):
            connector_type = sys.argv[idx + 1]

    if not os.path.exists(path):
        print(f"Error: File not found: {path}")
        sys.exit(1)

    results = run_all_checks(path, connector_type, verbose)
    # Exit 1 only for hard failures, not warnings
    sys.exit(0 if all(r.passed for r in results) else 1)
