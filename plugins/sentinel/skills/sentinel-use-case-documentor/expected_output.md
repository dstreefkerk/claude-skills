# UC-SENTINEL-BRUTEFORCE-001

## Name
UC-SENTINEL-BRUTEFORCE-001

## Purpose
Detect Brute Force Authentication Attacks Against Azure AD

The purpose of this use case design document is to fully describe this security detection, document the requirements to implement it within Microsoft Sentinel, and provide SOC response guidance.

## Problem Statement

Credentials are being harvested or stolen for unauthorized access through brute force authentication attempts.

Business Context: Credential stuffing and brute force attacks are a persistent threat against Azure AD tenants. Attackers use automated tools to test large volumes of username/password combinations harvested from data breaches. Early detection of these attacks is critical to prevent account compromise, lateral movement, and data exfiltration.

## Requirements Statement

NIST 800-53 AC-7 (Unsuccessful Logon Attempts) requires limiting consecutive invalid logon attempts. PCI-DSS Requirement 8.1.6 mandates limiting repeated access attempts by locking out the user ID after six attempts.

The SIEM system shall:
- Alert when 10 or more failed sign-in attempts occur from a single IP within 5 minutes
- Notify SOC team via configured notification channels
- Map alerts to Account and IP Address entities for investigation

## Design Specifications - Discrete Objectives (SMART)

Each objective must satisfy SMART criteria:

**Objective 1:**
- **Specific**: Detect when 10 or more failed Azure AD sign-in attempts occur from a single IP address within a 5-minute window
- **Measurable**: Alert triggered when FailedAttempts >= 10
- **Assignable**: SOC Tier 1 for initial triage, escalate to Tier 2 for confirmed attacks
- **Realistic**: SigninLogs available with <1 minute ingestion latency; threshold tested against baseline
- **Time-related**: Alert generated within 90 seconds of threshold breach

## Security Operations Center Notification

**Severity**: High

**Notification Method**:
- Microsoft Sentinel Incident Queue
- Email to soc-alerts@contoso.com
- Teams channel: #soc-high-priority

**Escalation Criteria**: Escalate to Tier 2 if attack involves privileged accounts or if source IP is internal.

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
| Analytics Rule | Detect-BruteForce-AzureAD | Detect brute force attempts |
| Data Connector | Azure Active Directory | SigninLogs ingestion |
| Playbook | Isolate-CompromisedAccount | Block account on confirmed compromise |
| Workbook | Authentication-Monitoring-Dashboard | Visualize sign-in patterns |
| Watchlist | VIP-Users | Prioritize alerts for executive accounts |

## Use Case Data Source Description

**Azure Active Directory Sign-in Logs**:
- **Connector Type**: Azure Active Directory
- **Table(s)**: SigninLogs
- **Ingestion Method**: Azure AD Diagnostic Settings → Log Analytics Workspace
- **Retention**: 90 days
- **Required Configuration**: Azure AD P1/P2 license; Diagnostic Settings configured to send SigninLogs

## Use Case Data Stream Analysis and Field Set

### Detection Logic (KQL Query)

```kql
SigninLogs
| where ResultType != "0"  // Failed sign-ins only
| where TimeGenerated > ago(5m)
| summarize
    FailedAttempts = count(),
    TargetAccounts = make_set(UserPrincipalName),
    FailureCodes = make_set(ResultType)
    by IPAddress, bin(TimeGenerated, 5m)
| where FailedAttempts >= 10
| extend AccountCount = array_length(TargetAccounts)
| project TimeGenerated, IPAddress, FailedAttempts, AccountCount, TargetAccounts, FailureCodes
```

### Query Parameters

| Parameter | Value | Readable |
|-----------|-------|----------|
| Query Frequency | PT5M | 5 minutes |
| Lookback Period | PT5M | 5 minutes |
| Trigger Threshold | 0 | Alert when results >= 1 |

### Required Fields

| Field Name | Data Type | Purpose | Example Value |
|------------|-----------|---------|---------------|
| ResultType | string | Identify failed sign-ins (non-zero = failure) | "50126" |
| UserPrincipalName | string | Target account being attacked | "user@contoso.com" |
| IPAddress | string | Source of authentication attempts | "203.0.113.50" |
| TimeGenerated | datetime | Timestamp for aggregation | "2025-01-19T10:30:00Z" |

### Entity Mappings

| Entity Type | Identifier | Column Mapping |
|-------------|------------|----------------|
| Account | Name | UserPrincipalName |
| IP | Address | IPAddress |

## MITRE ATT&CK Mapping

| Tactic | Technique ID | Technique Name | Sub-Technique |
|--------|--------------|----------------|---------------|
| Credential Access | T1110 | Brute Force | N/A |
| Credential Access | T1110.001 | Brute Force: Password Guessing | N/A |
| Credential Access | T1110.003 | Brute Force: Password Spraying | N/A |
| Credential Access | T1110.004 | Brute Force: Credential Stuffing | N/A |

## Cyber Kill Chain Analysis and Support

Indicate how this use case supports the Lockheed Martin Cyber Kill Chain:

| CKC Phase | Use Case Support |
|-----------|------------------|
| Reconnaissance | N/A |
| Weaponization | N/A |
| Delivery | N/A |
| Exploitation | **Primary**: Brute force attacks are exploitation attempts to gain valid credentials |
| Installation | N/A |
| C2: Command and Control | **Secondary**: Successful credential compromise enables attacker C2 via legitimate access |
| Actions on Objectives | N/A |

This detection primarily supports the **Exploitation** phase by identifying credential guessing attacks before they succeed.

## SOC Response Procedures

### Investigation Steps

1. **Initial Triage** (5 min):
   - Review the source IP address geolocation - is it expected for the organization?
   - Check if the IP is on any threat intelligence blocklists
   - Identify the target accounts - are they VIP/privileged users?

2. **Evidence Collection** (15 min):
   - Query SigninLogs for the full attack timeline from this IP
   - Check if any sign-ins succeeded (ResultType = 0) during or after the attack
   - Review Conditional Access logs for policy evaluations
   - Check Azure AD Identity Protection for related risk detections

3. **Escalation Criteria**:
   - Escalate to Tier 2 if any successful sign-in occurred
   - Escalate immediately if target includes privileged accounts (admin, service accounts)
   - Escalate if source IP is internal or VPN-connected

4. **Containment Actions**:
   - Block the source IP at the firewall/WAF if attack is ongoing
   - Force password reset for any successfully compromised accounts
   - Enable MFA if not already required
   - Consider Named Location blocking in Conditional Access

### False Positive Guidance

**Known False Positive Sources**:
- **Password sync issues**: Azure AD Connect password hash sync failures generate bulk failed sign-ins
- **Service accounts with expired credentials**: Automated services retrying with old passwords
- **Users with multiple devices**: Cached credentials on multiple devices during password change
- **MFA enrollment**: Users failing MFA challenges during enrollment appear as failed sign-ins

**How to Identify**:
- Check if the account is a service account (naming convention: svc-*, app-*)
- Review if failed sign-ins are from internal IPs only
- Check if ResultType indicates MFA failure (50074, 50076) vs password failure (50126)

## Assumptions and Limitations

**Assumptions**:
- Azure Active Directory connector is configured and ingesting SigninLogs
- SigninLogs table has <1 minute ingestion latency
- ResultType field is populated correctly (0 = success, non-zero = failure codes)
- Azure AD P1/P2 license is in place for full sign-in log retention

**Limitations**:
- Does not detect brute force against on-premises Active Directory (only Azure AD)
- VPN users with rotating IPs may generate false positives from multiple IP addresses
- Distributed attacks from botnet (1-2 attempts per IP) evade per-IP threshold detection
- 5-minute query window means attacks completing in <5 minutes may have slightly delayed detection
- Password spray attacks (one password, many accounts) require different detection logic

## Alternative Solutions and Discussion

**Alternative 1**: Azure AD Identity Protection Built-in Risk Detection
- **Description**: Use Azure AD IDP's ML-based risk detection for anomalous sign-ins
- **Pros**: No custom rule development, ML-driven, lower maintenance, integrates with Conditional Access
- **Cons**: Less customizable thresholds, requires Azure AD Premium P2 licensing, batch processing delays
- **Decision**: Rejected as primary detection due to licensing cost and need for real-time custom thresholds. Recommend using as complementary detection.

**Alternative 2**: Per-User Threshold Instead of Per-IP
- **Description**: Alert on N failed attempts to a single user account regardless of source IP
- **Pros**: Catches distributed attacks where multiple IPs target one account
- **Cons**: Higher false positive rate from legitimate user mistakes; less actionable (can't block by IP)
- **Decision**: Implement as separate complementary rule with higher threshold (25 attempts)

## Deliverable Profile

| Profile | Value |
|---------|-------|
| **File Name** | UC-SENTINEL-BRUTEFORCE-001.md |
| **Process Owner** | SOC Manager |
| **Original Author** | SOC Detection Engineering Team |
| **Policy/Procedure** | SEC-POL-001: Identity & Access Management Policy |
| **Industry Reference** | NIST 800-53 AC-7, MITRE ATT&CK T1110, PCI-DSS 8.1.6 |
| **Effective Date** | 2025-01-19 |
| **Document Last Modified** | 2025-01-19 |
| **Approval** | CISO |

## Version History

| Version | Date | Author | Changes | Approved By |
|---------|------|--------|---------|-------------|
| 1.0 | 2025-01-19 | SOC Detection Engineering Team | Initial use case documentation | CISO |
