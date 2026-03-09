# Best Practices & Reference

Best practices, quality checks, limitations, and reference data for ARM template generation.

---

## Severity Assignment

### High Severity (immediate security risk)
- Credential compromise (brute force, password spray)
- Privilege escalation
- Lateral movement
- Data exfiltration
- Malware/ransomware execution

### Medium Severity (potential security concern)
- Policy violations
- Suspicious behavior patterns
- Configuration changes
- Failed security events
- Anomalous network activity

### Low Severity (informational/monitoring)
- Compliance monitoring
- Audit events
- Baseline deviations

### Informational (tracking/statistics)
- Usage statistics
- Inventory changes
- Routine events

---

## Quality Checks

Before generation:
1. Test KQL query runs successfully
2. Provide conversation context about detection purpose
3. Verify required data tables exist
4. Ensure queryPeriod > queryFrequency

After generation:
1. Review MITRE mappings match intent
2. Validate entity mappings align with KQL output
3. Confirm frequency/period match operational needs
4. Verify customDetails surface key columns

### Azure Validation Rules

| Constraint | Limit | Error if Violated |
|------------|-------|-------------------|
| alertDescriptionFormat params | Max 3 | "Maximum allowed is 3" |
| entityMappings | Max 5 | Deployment fails |
| Entity type usage | Once per type | Deployment fails |
| templateVersion (custom rules) | Must NOT include | "can only be used if alertRuleTemplateName is not empty" |

---

## Limitations

### Technical
- Complex queries with dynamic schemas may need manual entity review
- Entity extraction works best with standard Sentinel tables
- Multi-table joins may need manual entity validation

### MITRE Mapping
- Mappings are intelligent suggestions, not guarantees
- Novel detection logic may need manual MITRE review
- Sub-techniques assigned when confidence is high

### Not Supported
- Fusion/ML rules (different rule type)
- NRT rules (different ARM schema)
- Multi-rule correlation (custom implementation needed)

---

## Common Sentinel Tables

### Azure AD Logs
- SigninLogs
- AuditLogs
- AADNonInteractiveUserSignInLogs
- AADServicePrincipalSignInLogs

### Microsoft Defender
- DeviceEvents
- DeviceFileEvents
- DeviceNetworkEvents
- DeviceProcessEvents
- DeviceRegistryEvents
- DeviceLogonEvents

### Security Events
- SecurityEvent
- WindowsEvent
- Syslog
- CommonSecurityLog

### Cloud Services
- AzureActivity
- AzureDiagnostics
- OfficeActivity
- AWSCloudTrail

---

## Typical Workflows

### Threat Research to Production
1. Develop KQL during threat hunting
2. Validate query returns accurate detections
3. Generate ARM template with auto-mappings
4. Review MITRE and entity mappings
5. Deploy via CI/CD pipeline

### Multi-Environment Deployment
1. Create detection in dev workspace
2. Generate ARM template with workspace parameter
3. Deploy to staging (disabled)
4. Validate rule behavior
5. Deploy to production (enabled)
