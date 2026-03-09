"""
KQL Query Validator Module

Validates KQL queries for syntax correctness, best practices compliance,
entity mapping validation, and MITRE ATT&CK framework alignment.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    ERROR = "ERROR"        # Prevents query execution
    WARNING = "WARNING"    # May cause issues
    INFO = "INFO"          # Best practice recommendation


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    severity: ValidationSeverity
    category: str
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Query validation result."""
    is_valid: bool
    issues: List[ValidationIssue]
    warnings_count: int
    errors_count: int
    info_count: int


class KQLValidator:
    """Validates KQL queries for correctness and best practices."""

    # Valid MITRE ATT&CK tactics (version 18)
    VALID_MITRE_TACTICS = {
        'Reconnaissance', 'Resource Development', 'Initial Access', 'Execution',
        'Persistence', 'Privilege Escalation', 'Defense Evasion', 'Credential Access',
        'Discovery', 'Lateral Movement', 'Collection', 'Command and Control',
        'Exfiltration', 'Impact'
    }

    # Common Sentinel tables
    SENTINEL_TABLES = {
        'SecurityEvent', 'SigninLogs', 'AADSignInEventsBeta', 'AuditLogs',
        'OfficeActivity', 'AzureActivity', 'AzureDiagnostics',
        'DeviceProcessEvents', 'DeviceNetworkEvents', 'DeviceFileEvents',
        'DeviceRegistryEvents', 'DeviceLogonEvents', 'DeviceEvents',
        'EmailEvents', 'CloudAppEvents', 'IdentityInfo',
        'ThreatIntelligenceIndicator', 'Watchlist', 'Syslog', 'CommonSecurityLog',
        'ASimAuthenticationEventLogs', 'ASimNetworkSessionLogs', 'ASimProcessEventLogs',
        'ASimFileEventLogs', 'ASimDnsActivityLogs', 'ASimWebSessionLogs',
        'ASimRegistryEventLogs', 'ASimAuditEventLogs'
    }

    # Valid entity types for mapping
    VALID_ENTITY_TYPES = {
        'Account', 'Host', 'IP', 'URL', 'FileHash', 'File', 'Process',
        'CloudApplication', 'DNS', 'AzureResource', 'MailCluster',
        'MailMessage', 'Mailbox', 'SubmissionMail', 'SecurityGroup',
        'RegistryKey', 'RegistryValue'
    }

    # Prohibited patterns in analytics rules
    PROHIBITED_PATTERNS = [
        (r'search\s+\*', 'search * is prohibited in analytics rules'),
        (r'union\s+\*', 'union * is prohibited in analytics rules')
    ]

    def __init__(self):
        self.issues: List[ValidationIssue] = []
        self.query_lines: List[str] = []

    def validate_query(self, query: str, context: str = 'general') -> ValidationResult:
        """
        Validate a KQL query.

        Args:
            query: KQL query string
            context: Context type ('general', 'analytics_rule', 'hunting', 'workbook')

        Returns:
            ValidationResult with all detected issues
        """
        self.issues = []
        self.query_lines = query.strip().split('\n')

        # Basic syntax validation
        self._validate_syntax()

        # Best practices validation
        self._validate_best_practices()

        # Context-specific validation
        if context == 'analytics_rule':
            self._validate_analytics_rule()

        # Count issues by severity
        errors = sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)
        warnings = sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)
        info = sum(1 for i in self.issues if i.severity == ValidationSeverity.INFO)

        return ValidationResult(
            is_valid=(errors == 0),
            issues=self.issues,
            warnings_count=warnings,
            errors_count=errors,
            info_count=info
        )

    def validate_entity_mapping(self, entity_mappings: List[Dict[str, Any]]) -> ValidationResult:
        """
        Validate entity mappings for analytics rule.

        Args:
            entity_mappings: List of entity mapping configurations

        Returns:
            ValidationResult
        """
        self.issues = []

        if not entity_mappings:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category='entity_mapping',
                message='No entity mappings configured - limits incident correlation'
            ))
            return self._create_result()

        if len(entity_mappings) > 10:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category='entity_mapping',
                message=f'Too many entity mappings: {len(entity_mappings)}. Maximum is 10.'
            ))

        for idx, mapping in enumerate(entity_mappings):
            entity_type = mapping.get('entityType')

            if not entity_type:
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category='entity_mapping',
                    message=f'Entity mapping {idx + 1}: Missing entityType'
                ))
                continue

            if entity_type not in self.VALID_ENTITY_TYPES:
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category='entity_mapping',
                    message=f'Entity mapping {idx + 1}: Invalid entityType "{entity_type}"',
                    suggestion=f'Valid types: {", ".join(sorted(self.VALID_ENTITY_TYPES))}'
                ))

            # Check identifiers
            identifiers = mapping.get('fieldMappings', [])
            if not identifiers:
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category='entity_mapping',
                    message=f'Entity mapping {idx + 1}: No field mappings configured'
                ))

            if len(identifiers) > 3:
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category='entity_mapping',
                    message=f'Entity mapping {idx + 1}: More than 3 identifiers may affect grouping performance'
                ))

        # Check for recommended entity combination (limit to 3 for grouping)
        if len(entity_mappings) > 3:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category='entity_mapping',
                message=f'{len(entity_mappings)} entities mapped. Consider limiting to 3 strong identifiers for optimal incident grouping.',
                suggestion='Refine incident grouping settings if mapping >3 entities'
            ))

        return self._create_result()

    def validate_mitre_mapping(self, tactics: List[str], techniques: Optional[List[str]] = None) -> ValidationResult:
        """
        Validate MITRE ATT&CK framework mappings.

        Args:
            tactics: List of MITRE tactics
            techniques: Optional list of technique IDs

        Returns:
            ValidationResult
        """
        self.issues = []

        if not tactics:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category='mitre_mapping',
                message='No MITRE ATT&CK tactics mapped - reduces threat context',
                suggestion='Map detection to relevant MITRE ATT&CK tactics'
            ))
            return self._create_result()

        # Validate tactics
        for tactic in tactics:
            if tactic not in self.VALID_MITRE_TACTICS:
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category='mitre_mapping',
                    message=f'Invalid MITRE tactic: "{tactic}"',
                    suggestion=f'Valid tactics: {", ".join(sorted(self.VALID_MITRE_TACTICS))}'
                ))

        # Validate techniques if provided
        if techniques:
            technique_pattern = re.compile(r'^T\d{4}(\.\d{3})?$')
            for technique in techniques:
                if not technique_pattern.match(technique):
                    self.issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category='mitre_mapping',
                        message=f'Technique ID "{technique}" does not match standard format (T####[.###])',
                        suggestion='Use format: T1234 or T1234.001'
                    ))

        return self._create_result()

    def _validate_syntax(self):
        """Basic syntax validation."""
        query_text = '\n'.join(self.query_lines)

        # Check for unclosed parentheses
        open_parens = query_text.count('(')
        close_parens = query_text.count(')')
        if open_parens != close_parens:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category='syntax',
                message=f'Mismatched parentheses: {open_parens} open, {close_parens} close'
            ))

        # Check for unclosed brackets
        open_brackets = query_text.count('[')
        close_brackets = query_text.count(']')
        if open_brackets != close_brackets:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category='syntax',
                message=f'Mismatched brackets: {open_brackets} open, {close_brackets} close'
            ))

        # Check for common typos
        common_typos = {
            'sumarize': 'summarize',
            'were': 'where',
            'projcet': 'project',
            'exten': 'extend'
        }

        for i, line in enumerate(self.query_lines):
            for typo, correct in common_typos.items():
                if typo in line.lower():
                    self.issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category='syntax',
                        message=f'Possible typo: "{typo}" (did you mean "{correct}"?)',
                        line_number=i + 1
                    ))

    def _validate_best_practices(self):
        """Validate against best practices."""
        query_text = '\n'.join(self.query_lines)

        # Check for TimeGenerated column in output (required for analytics rules)
        if 'project' in query_text:
            # Find last project statement
            last_project_line = None
            for i in range(len(self.query_lines) - 1, -1, -1):
                if '| project' in self.query_lines[i]:
                    last_project_line = self.query_lines[i]
                    break

            if last_project_line and 'TimeGenerated' not in last_project_line:
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category='best_practice',
                    message='TimeGenerated not included in final project - may cause issues in analytics rules',
                    suggestion='Include TimeGenerated in project statement'
                ))

        # Check for hardcoded IP addresses or usernames (should use watchlists)
        ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        for i, line in enumerate(self.query_lines):
            if '!=' in line or '!in' in line or 'where' in line:
                ips = ip_pattern.findall(line)
                if ips:
                    self.issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        category='best_practice',
                        message=f'Hardcoded IP address(es) found: {", ".join(ips)}',
                        line_number=i + 1,
                        suggestion='Consider using watchlists for exception management'
                    ))

        # Check for comments at end of lines
        for i, line in enumerate(self.query_lines):
            if line.strip() and not line.strip().startswith('//'):
                if '//' in line and '|' in line:
                    self.issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category='best_practice',
                        message='Inline comment may cause parsing issues',
                        line_number=i + 1,
                        suggestion='Place comments on separate lines'
                    ))

        # Check for dynamic arrays with proper syntax
        if 'dynamic(' in query_text:
            for i, line in enumerate(self.query_lines):
                if 'dynamic(' in line and not re.search(r'dynamic\s*\(\s*\[', line):
                    self.issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category='syntax',
                        message='dynamic() should use array syntax with brackets',
                        line_number=i + 1,
                        suggestion='Use: dynamic(["item1", "item2"])'
                    ))

    def _validate_analytics_rule(self):
        """Validate analytics rule specific requirements."""
        query_text = '\n'.join(self.query_lines)

        # Check for prohibited patterns
        for pattern, message in self.PROHIBITED_PATTERNS:
            if re.search(pattern, query_text, re.IGNORECASE):
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category='analytics_rule',
                    message=message
                ))

        # Check query length (max 10,000 characters for analytics rules)
        if len(query_text) > 10000:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category='analytics_rule',
                message=f'Query length ({len(query_text)} chars) exceeds 10,000 character limit',
                suggestion='Move large lists to watchlists or user-defined functions'
            ))

        # Check for bag_unpack without null protection
        if 'bag_unpack' in query_text and 'column_ifexists' not in query_text:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category='analytics_rule',
                message='bag_unpack used without column_ifexists protection',
                suggestion='Use column_ifexists("FieldName", "") to handle missing columns'
            ))

        # Check for cross-workspace query limits
        workspace_count = query_text.count('workspace(')
        if workspace_count > 20:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category='analytics_rule',
                message=f'Too many workspaces referenced: {workspace_count}. Maximum is 20 for analytics rules.',
                suggestion='Reduce workspace count or split into multiple rules'
            ))

    def validate_watchlist_usage(self, query: str, watchlist_names: List[str]) -> ValidationResult:
        """
        Validate watchlist integration patterns.

        Args:
            query: KQL query
            watchlist_names: List of watchlist names used

        Returns:
            ValidationResult
        """
        self.issues = []

        for watchlist_name in watchlist_names:
            # Check if SearchKey is used for joins
            pattern = f"_GetWatchlist\\('{watchlist_name}'\\)"
            if pattern in query or f'_GetWatchlist("{watchlist_name}")' in query:
                # Check if SearchKey is projected
                if 'SearchKey' not in query:
                    self.issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category='watchlist',
                        message=f'Watchlist "{watchlist_name}" not using SearchKey for joins',
                        suggestion='Use SearchKey field for optimal performance: | project SearchKey'
                    ))

        return self._create_result()

    def _create_result(self) -> ValidationResult:
        """Create ValidationResult from current issues."""
        errors = sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)
        warnings = sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)
        info = sum(1 for i in self.issues if i.severity == ValidationSeverity.INFO)

        return ValidationResult(
            is_valid=(errors == 0),
            issues=self.issues,
            warnings_count=warnings,
            errors_count=errors,
            info_count=info
        )


def format_validation_result(result: ValidationResult) -> str:
    """Format validation result as human-readable text."""
    lines = ["=" * 80]
    lines.append("KQL QUERY VALIDATION REPORT")
    lines.append("=" * 80)
    lines.append("")

    # Summary
    status = "✓ VALID" if result.is_valid else "✗ INVALID"
    lines.append(f"Status: {status}")
    lines.append(f"Errors: {result.errors_count}")
    lines.append(f"Warnings: {result.warnings_count}")
    lines.append(f"Info: {result.info_count}")
    lines.append("")

    if not result.issues:
        lines.append("✓ No issues found - query is valid")
        return '\n'.join(lines)

    # Group by severity
    for severity in [ValidationSeverity.ERROR, ValidationSeverity.WARNING, ValidationSeverity.INFO]:
        severity_issues = [i for i in result.issues if i.severity == severity]
        if not severity_issues:
            continue

        lines.append(f"\n{severity.value} ({len(severity_issues)}):")
        lines.append("-" * 80)

        for idx, issue in enumerate(severity_issues, 1):
            lines.append(f"\n{idx}. [{issue.category}] {issue.message}")
            if issue.line_number:
                lines.append(f"   Line: {issue.line_number}")
            if issue.suggestion:
                lines.append(f"   Suggestion: {issue.suggestion}")

    return '\n'.join(lines)


# Example usage
if __name__ == "__main__":
    validator = KQLValidator()

    # Test query validation
    test_query = """
SecurityEvent
| where TimeGenerated > ago(1h)
| where EventID == 4625
| where AccountName != "admin"
| project TimeGenerated, Computer, AccountName, IpAddress
"""

    result = validator.validate_query(test_query, context='analytics_rule')
    print(format_validation_result(result))

    # Test entity mapping validation
    entity_mappings = [
        {
            'entityType': 'Account',
            'fieldMappings': [
                {'identifier': 'Name', 'columnName': 'AccountName'}
            ]
        },
        {
            'entityType': 'IP',
            'fieldMappings': [
                {'identifier': 'Address', 'columnName': 'IpAddress'}
            ]
        }
    ]

    entity_result = validator.validate_entity_mapping(entity_mappings)
    print("\n" + format_validation_result(entity_result))

    # Test MITRE mapping validation
    mitre_result = validator.validate_mitre_mapping(
        tactics=['Credential Access', 'Initial Access'],
        techniques=['T1110', 'T1078']
    )
    print("\n" + format_validation_result(mitre_result))
