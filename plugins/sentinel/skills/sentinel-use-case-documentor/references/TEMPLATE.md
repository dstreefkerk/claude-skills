# SOC/SIEM Use Case Template

> Based on industry-standard SOC use case methodology. Copy this template and replace placeholders with extracted/inferred values.

---

## Name
{USE_CASE_ID}

## Purpose
{RULE_DESCRIPTION}

The purpose of this use case design document is to fully describe this security detection, document the requirements to implement it within Microsoft Sentinel, and provide SOC response guidance.

## Problem Statement

{INFERRED_PROBLEM_FROM_TACTIC}

[HUMAN INPUT REQUIRED]: Expand on the specific security problem or risk this use case mitigates. Answer the "5 Ws" - What is the issue? Who is affected? When does it occur? Where in the environment? Why is it important?

## Requirements Statement

{COMPLIANCE_FRAMEWORKS_FROM_TECHNIQUES}

The SIEM system shall:
- Alert when {TRIGGER_CONDITION}
- Notify {NOTIFICATION_CHANNELS}
- Map alerts to {ENTITY_TYPES}

[HUMAN INPUT REQUIRED]: Describe additional actions the SIEM system or SOC team must take.

## Design Specifications - Discrete Objectives (SMART)

Each objective must satisfy SMART criteria:

**Objective 1:**
- **Specific**: {WHAT_EXACTLY_DETECTED}
- **Measurable**: {ALERT_THRESHOLD_CONDITION}
- **Assignable**: {WHO_IS_RESPONSIBLE}
- **Realistic**: {DATA_SOURCE_AND_LATENCY}
- **Time-related**: {DETECTION_TIMING_SLA}

[HUMAN INPUT REQUIRED]: Add additional objectives if needed.

## Security Operations Center Notification

**Severity**: {RULE_SEVERITY}

**Notification Method**:
- {NOTIFICATION_CHANNELS}
- [HUMAN INPUT REQUIRED]: Add specific notification channels (e.g., Slack, PagerDuty, Teams, Email DL)

**Escalation Criteria**: [HUMAN INPUT REQUIRED]

**SOC Response SLA**:
| Severity | Priority | Response SLA |
|----------|----------|--------------|
| Informational | P4 | 24 hours |
| Low | P3 | 8 hours |
| Medium | P2 | 4 hours |
| High | P1 | 1 hour |

## Use Case Component Name(s)

List Sentinel components that implement this use case:

| Component Type | Name | Purpose |
|----------------|------|---------|
| Analytics Rule | {RULE_DISPLAY_NAME} | {DETECTION_PURPOSE} |
| Data Connector | {CONNECTOR_NAME} | {DATA_SOURCE} |
| Playbook | [HUMAN INPUT REQUIRED] | Automated response |
| Workbook | [HUMAN INPUT REQUIRED] | Visualization |
| Watchlist | [HUMAN INPUT REQUIRED] | Reference data |

## Use Case Data Source Description

**{DATA_SOURCE_NAME}**:
- **Connector Type**: {CONNECTOR_TYPE}
- **Table(s)**: {TABLE_NAME}
- **Ingestion Method**: {INGESTION_METHOD}
- **Retention**: [HUMAN INPUT REQUIRED]
- **Required Configuration**: [HUMAN INPUT REQUIRED]

[HUMAN INPUT REQUIRED]: Indicate if the data source is currently available or steps needed to enable it.

## Use Case Data Stream Analysis and Field Set

### Detection Logic (KQL Query)

```kql
{KQL_QUERY}
```

### Query Parameters

| Parameter | Value | Readable |
|-----------|-------|----------|
| Query Frequency | {QUERY_FREQUENCY_ISO} | {QUERY_FREQUENCY_READABLE} |
| Lookback Period | {QUERY_PERIOD_ISO} | {QUERY_PERIOD_READABLE} |
| Trigger Threshold | {TRIGGER_THRESHOLD} | Alert when results >= {THRESHOLD} |

### Required Fields

| Field Name | Data Type | Purpose | Example Value |
|------------|-----------|---------|---------------|
| {FIELD_1} | {TYPE} | {PURPOSE} | {EXAMPLE} |
| {FIELD_2} | {TYPE} | {PURPOSE} | {EXAMPLE} |

[HUMAN INPUT REQUIRED]: Complete field details and add optional enrichment fields.

### Entity Mappings

| Entity Type | Identifier | Column Mapping |
|-------------|------------|----------------|
| {ENTITY_TYPE} | {IDENTIFIER} | {COLUMN_NAME} |

## MITRE ATT&CK Mapping

| Tactic | Technique ID | Technique Name | Sub-Technique |
|--------|--------------|----------------|---------------|
| {TACTIC} | {TECHNIQUE_ID} | {TECHNIQUE_NAME} | {SUB_TECHNIQUE_OR_NA} |

## Cyber Kill Chain Analysis and Support

Indicate how this use case supports the Lockheed Martin Cyber Kill Chain:

| CKC Phase | Use Case Support |
|-----------|------------------|
| Reconnaissance | {SUPPORT_OR_NA} |
| Weaponization | {SUPPORT_OR_NA} |
| Delivery | {SUPPORT_OR_NA} |
| Exploitation | {SUPPORT_OR_NA} |
| Installation | {SUPPORT_OR_NA} |
| C2: Command and Control | {SUPPORT_OR_NA} |
| Actions on Objectives | {SUPPORT_OR_NA} |

[HUMAN INPUT REQUIRED]: Validate the kill chain mapping and explain why specific phases apply.

## SOC Response Procedures

### Investigation Steps

{INVESTIGATION_STEPS_FROM_KQL_COMMENTS}

[HUMAN INPUT REQUIRED]: Define step-by-step investigation procedure:
1. Initial triage actions
2. Evidence collection steps
3. Escalation criteria
4. Containment actions

### False Positive Guidance

{FALSE_POSITIVE_FROM_KQL_COMMENTS}

[HUMAN INPUT REQUIRED]: Document known false positive sources and how to identify them.

## Assumptions and Limitations

**Assumptions**:
- {DATA_CONNECTOR} connector is configured and ingesting data
- {TABLE_NAME} table has expected latency (<{LATENCY})
- {KEY_FIELD} field is populated correctly
- [HUMAN INPUT REQUIRED]: Add environment-specific assumptions

**Limitations**:
- {LIMITATION_1_FROM_QUERY_ANALYSIS}
- Query frequency ({QUERY_FREQUENCY}) introduces detection delay
- [HUMAN INPUT REQUIRED]: Document coverage gaps

## Alternative Solutions and Discussion

[HUMAN INPUT REQUIRED]: Document alternative detection approaches considered:

**Alternative 1**: {ALTERNATIVE_NAME}
- **Description**: How it would work
- **Pros**: Advantages
- **Cons**: Disadvantages
- **Decision**: Why selected or rejected

## Deliverable Profile

| Profile | Value |
|---------|-------|
| **File Name** | {USE_CASE_ID}.md |
| **Process Owner** | [HUMAN INPUT REQUIRED] |
| **Original Author** | {AUTHOR_FROM_DESCRIPTION} |
| **Policy/Procedure** | [HUMAN INPUT REQUIRED] |
| **Industry Reference** | {MITRE_ATTACK_REFERENCE}, {COMPLIANCE_FRAMEWORK} |
| **Effective Date** | {CURRENT_DATE} |
| **Document Last Modified** | {CURRENT_DATE} |
| **Approval** | [HUMAN INPUT REQUIRED] |

## Version History

| Version | Date | Author | Changes | Approved By |
|---------|------|--------|---------|-------------|
| 1.0 | {CURRENT_DATE} | {AUTHOR} | Initial use case documentation | [HUMAN INPUT REQUIRED] |

---

## Summary of Required Human Input

This document was auto-generated from available context. Search for `[HUMAN INPUT REQUIRED]` to find sections needing completion:

1. Problem Statement - expand business context
2. Requirements Statement - additional SIEM actions
3. SOC Notification - channels and escalation
4. Component Names - playbooks, workbooks, watchlists
5. Data Source Description - retention and config
6. Field Set - complete field details
7. Cyber Kill Chain - validate mapping
8. Investigation Steps - detailed procedure
9. False Positive Guidance - known sources
10. Assumptions & Limitations - environment-specific
11. Alternative Solutions - approaches considered
12. Deliverable Profile - owner, policy, approval

**Review Checklist**:
- [ ] Validate all technical details (queries, fields, data sources)
- [ ] Complete all [HUMAN INPUT REQUIRED] sections
- [ ] Review SMART objectives for completeness
- [ ] Verify compliance mappings are accurate
- [ ] Update version history with author and approver
- [ ] Confirm notification and escalation procedures
