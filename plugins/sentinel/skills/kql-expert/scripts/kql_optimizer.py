"""
KQL Query Optimizer Module

Analyzes KQL queries for performance issues and provides optimization
recommendations based on Microsoft Sentinel best practices.
"""

from typing import List, Optional
from dataclasses import dataclass
from enum import Enum
import re


class ImpactLevel(Enum):
    """Optimization impact severity levels."""
    CRITICAL = "CRITICAL"  # May cause timeouts or auto-disable
    HIGH = "HIGH"          # Significant performance improvement
    MEDIUM = "MEDIUM"      # Moderate improvement
    LOW = "LOW"            # Minor improvement


@dataclass
class OptimizationIssue:
    """Represents a detected performance issue."""
    issue_type: str
    severity: ImpactLevel
    line_number: Optional[int]
    description: str
    recommendation: str
    example_fix: Optional[str] = None


@dataclass
class OptimizationReport:
    """Complete optimization analysis report."""
    original_query: str
    issues: List[OptimizationIssue]
    optimized_query: Optional[str] = None
    estimated_improvement: Optional[str] = None


class KQLOptimizer:
    """Analyzes and optimizes KQL queries for performance."""

    def __init__(self):
        self.issues: List[OptimizationIssue] = []
        self.query_lines: List[str] = []

    def analyze_query(self, query: str) -> OptimizationReport:
        """
        Analyze a KQL query for performance issues.

        Args:
            query: KQL query string

        Returns:
            OptimizationReport with detected issues and recommendations
        """
        self.issues = []
        self.query_lines = query.strip().split('\n')

        # Run all analysis checks
        self._check_time_filtering()
        self._check_string_operators()
        self._check_filter_placement()
        self._check_join_optimization()
        self._check_aggregation_patterns()
        self._check_column_pruning()
        self._check_search_operators()
        self._check_case_sensitivity()
        self._check_asim_patterns()
        self._check_analytics_rule_specific()

        # Generate optimized query if critical issues found
        optimized_query = self._generate_optimized_query(query)

        # Estimate improvement
        improvement = self._estimate_improvement()

        return OptimizationReport(
            original_query=query,
            issues=sorted(self.issues, key=lambda x: x.severity.value),
            optimized_query=optimized_query,
            estimated_improvement=improvement
        )

    def _check_time_filtering(self):
        """Check for missing or late time filters."""
        query_text = '\n'.join(self.query_lines)

        # Check if TimeGenerated filter exists
        if 'TimeGenerated' not in query_text and 'starttime=' not in query_text:
            self.issues.append(OptimizationIssue(
                issue_type='missing_time_filter',
                severity=ImpactLevel.CRITICAL,
                line_number=None,
                description='Query does not include TimeGenerated filter',
                recommendation='Always filter on TimeGenerated immediately after table reference to leverage time-based partitioning',
                example_fix='| where TimeGenerated > ago(1h)'
            ))

        # Check if time filter is early in the query
        for i, line in enumerate(self.query_lines):
            if 'TimeGenerated' in line and 'where' in line:
                # Check if table reference appears before this line
                table_line = None
                for j in range(i):
                    if self._is_table_reference(self.query_lines[j]):
                        table_line = j
                        break

                if table_line is not None and (i - table_line) > 2:
                    self.issues.append(OptimizationIssue(
                        issue_type='late_time_filter',
                        severity=ImpactLevel.HIGH,
                        line_number=i + 1,
                        description='TimeGenerated filter appears too late in query',
                        recommendation='Place TimeGenerated filter immediately after table reference (within first 2 lines)',
                        example_fix='Move "| where TimeGenerated > ago(Xh)" to line immediately after table name'
                    ))

    def _check_string_operators(self):
        """Check for inefficient string operators."""
        for i, line in enumerate(self.query_lines):
            # Check for 'contains' when 'has' might work
            if ' contains ' in line.lower() and 'has' not in line.lower():
                self.issues.append(OptimizationIssue(
                    issue_type='contains_instead_of_has',
                    severity=ImpactLevel.HIGH,
                    line_number=i + 1,
                    description=f'Using "contains" operator which performs full column scan',
                    recommendation='Replace "contains" with "has" for term-based searching (3+ character terms). Use "contains" only for substring matching within words.',
                    example_fix='| where CommandLine has "powershell"  // instead of contains'
                ))

            # Check for tolower/toupper before comparison
            if re.search(r'tolower\([^)]+\)\s*==|toupper\([^)]+\)\s*==', line):
                self.issues.append(OptimizationIssue(
                    issue_type='tolower_comparison',
                    severity=ImpactLevel.MEDIUM,
                    line_number=i + 1,
                    description='Using tolower() or toupper() before comparison is inefficient',
                    recommendation='Use case-insensitive operators (=~, has, in~) instead of converting case',
                    example_fix='| where Field =~ "value"  // instead of tolower(Field) == "value"'
                ))

    def _check_filter_placement(self):
        """Check for filters placed after expensive operations."""
        expensive_operators = ['join', 'summarize', 'extend', 'parse', 'mv-expand']

        for i, line in enumerate(self.query_lines):
            # Check if where appears after expensive operations
            if '| where' in line:
                for j in range(i - 1, -1, -1):
                    prev_line = self.query_lines[j].strip()
                    for op in expensive_operators:
                        if f'| {op}' in prev_line:
                            self.issues.append(OptimizationIssue(
                                issue_type='filter_after_expensive_op',
                                severity=ImpactLevel.HIGH,
                                line_number=i + 1,
                                description=f'Filter appears after expensive "{op}" operation',
                                recommendation=f'Move filters before {op} operation to reduce data volume processed',
                                example_fix=f'Reorder: apply "where" clauses before "| {op}"'
                            ))
                            break

    def _check_join_optimization(self):
        """Check join patterns for optimization opportunities."""
        for i, line in enumerate(self.query_lines):
            if '| join' in line:
                # Check for missing join hints
                if 'hint.strategy' not in line and 'hint.shufflekey' not in line:
                    self.issues.append(OptimizationIssue(
                        issue_type='missing_join_hint',
                        severity=ImpactLevel.MEDIUM,
                        line_number=i + 1,
                        description='Join operation without performance hints',
                        recommendation='Use hint.strategy=broadcast for small tables (<100KB) or hint.shufflekey for high-cardinality keys (>1M distinct values)',
                        example_fix='| join kind=inner hint.strategy=broadcast (...) on Key'
                    ))

                # Check if subquery has time filter
                # Look ahead for subquery
                subquery_start = i + 1
                paren_count = 0
                has_time_filter = False

                for j in range(i, min(i + 20, len(self.query_lines))):
                    if '(' in self.query_lines[j]:
                        paren_count += self.query_lines[j].count('(')
                    if ')' in self.query_lines[j]:
                        paren_count -= self.query_lines[j].count(')')

                    if paren_count > 0 and 'TimeGenerated' in self.query_lines[j]:
                        has_time_filter = True
                        break

                    if paren_count == 0 and j > i:
                        break

                if not has_time_filter:
                    self.issues.append(OptimizationIssue(
                        issue_type='join_missing_time_filter',
                        severity=ImpactLevel.CRITICAL,
                        line_number=i + 1,
                        description='Join subquery does not include TimeGenerated filter',
                        recommendation='Add TimeGenerated filter to join subquery - time scope does not automatically propagate',
                        example_fix='| join kind=inner (Table | where TimeGenerated > ago(1h) | ...) on Key'
                    ))

    def _check_aggregation_patterns(self):
        """Check aggregation optimization opportunities."""
        for i, line in enumerate(self.query_lines):
            # Check for sort + take instead of top
            if '| sort by' in line or '| order by' in line:
                # Check if next line (or within next 2 lines) has 'take'
                for j in range(i + 1, min(i + 3, len(self.query_lines))):
                    if '| take' in self.query_lines[j]:
                        self.issues.append(OptimizationIssue(
                            issue_type='sort_take_instead_of_top',
                            severity=ImpactLevel.MEDIUM,
                            line_number=i + 1,
                            description='Using "sort | take" pattern instead of "top"',
                            recommendation='Replace "sort by Field | take N" with "top N by Field" for better performance',
                            example_fix='| top 100 by TimeGenerated desc'
                        ))
                        break

    def _check_column_pruning(self):
        """Check for missing column pruning."""
        query_text = '\n'.join(self.query_lines)
        has_project = '| project' in query_text
        has_join = '| join' in query_text
        has_summarize = '| summarize' in query_text

        # If query has join or summarize but no project before them
        if (has_join or has_summarize) and not has_project:
            # Check if project appears before join/summarize
            project_found_early = False
            for i, line in enumerate(self.query_lines):
                if '| project' in line:
                    project_found_early = True
                if project_found_early:
                    break
                if '| join' in line or '| summarize' in line:
                    self.issues.append(OptimizationIssue(
                        issue_type='missing_column_pruning',
                        severity=ImpactLevel.MEDIUM,
                        line_number=i + 1,
                        description='No column pruning before expensive operation',
                        recommendation='Use "| project" to select only needed columns before join or summarize operations',
                        example_fix='| project Field1, Field2, Field3  // Add before join/summarize'
                    ))
                    break

    def _check_search_operators(self):
        """Check for inefficient search operators."""
        for i, line in enumerate(self.query_lines):
            # Check for 'search *' or 'union *'
            if ' search *' in line or ' search*' in line:
                self.issues.append(OptimizationIssue(
                    issue_type='search_wildcard',
                    severity=ImpactLevel.CRITICAL,
                    line_number=i + 1,
                    description='Using "search *" which scans all tables in workspace',
                    recommendation='Specify explicit table names or use "where" with specific fields',
                    example_fix='SecurityEvent | where ... // Replace search * with specific table'
                ))

            if ' union *' in line or ' union*' in line or '| union withsource' in line and '*' in line:
                self.issues.append(OptimizationIssue(
                    issue_type='union_wildcard',
                    severity=ImpactLevel.CRITICAL,
                    line_number=i + 1,
                    description='Using "union *" which scans all tables in workspace',
                    recommendation='Explicitly list tables in union operation',
                    example_fix='union SecurityEvent, SigninLogs, AuditLogs'
                ))

    def _check_case_sensitivity(self):
        """Check for case-insensitive operators when case-sensitive would work."""
        case_insensitive_operators = ['=~', 'in~', 'has', 'contains', 'startswith', 'endswith']

        for i, line in enumerate(self.query_lines):
            for op in case_insensitive_operators:
                if f' {op} ' in line.lower():
                    # Suggest case-sensitive variant if comparing to known values
                    case_sensitive_op = op.replace('~', '') + '_cs' if op.endswith('~') else op + '_cs'
                    self.issues.append(OptimizationIssue(
                        issue_type='case_insensitive_operator',
                        severity=ImpactLevel.LOW,
                        line_number=i + 1,
                        description=f'Using case-insensitive operator "{op}"',
                        recommendation=f'Consider using case-sensitive variant "{case_sensitive_op}" if you know the exact case',
                        example_fix=f'| where Field == "Value"  // or {case_sensitive_op} if case-insensitive needed'
                    ))

    def _check_asim_patterns(self):
        """Check ASIM parser usage patterns."""
        for i, line in enumerate(self.query_lines):
            # Check for ASIM parsers
            if '_Im_' in line or '_ASim_' in line or 'im' in line.lower():
                # Check for filtering parameters
                if '(' not in line or 'starttime=' not in line:
                    self.issues.append(OptimizationIssue(
                        issue_type='asim_missing_filters',
                        severity=ImpactLevel.HIGH,
                        line_number=i + 1,
                        description='ASIM parser called without filtering parameters',
                        recommendation='Always pass filtering parameters (starttime, endtime, etc.) to ASIM parsers to push filters down to source tables',
                        example_fix='_Im_Authentication(starttime=ago(1h), endtime=now(), eventresult="Failure")'
                    ))

                # Check for parameter-less legacy parsers
                if '_ASim_' in line:
                    self.issues.append(OptimizationIssue(
                        issue_type='legacy_asim_parser',
                        severity=ImpactLevel.MEDIUM,
                        line_number=i + 1,
                        description='Using legacy parameter-less ASIM parser (_ASim_)',
                        recommendation='Replace with filtering-enabled parser (_Im_) and pass filtering parameters',
                        example_fix='_Im_Authentication(starttime=ago(1h), endtime=now())'
                    ))

    def _check_analytics_rule_specific(self):
        """Check for analytics rule specific issues."""
        query_text = '\n'.join(self.query_lines)

        # Check for bag_unpack without null protection
        if 'bag_unpack' in query_text and 'column_ifexists' not in query_text:
            for i, line in enumerate(self.query_lines):
                if 'bag_unpack' in line:
                    self.issues.append(OptimizationIssue(
                        issue_type='bag_unpack_no_protection',
                        severity=ImpactLevel.MEDIUM,
                        line_number=i + 1,
                        description='Using bag_unpack without null protection',
                        recommendation='Use column_ifexists() to handle missing columns gracefully',
                        example_fix='| extend Field = column_ifexists("FieldName", "")'
                    ))

    def _is_table_reference(self, line: str) -> bool:
        """Check if line contains a table reference."""
        line = line.strip()
        # Simple heuristic: line starts with capital letter and no pipe
        if not line.startswith('|') and line and line[0].isupper():
            return True
        return False

    def _generate_optimized_query(self, original_query: str) -> Optional[str]:
        """Generate optimized version of query if critical issues found."""
        # This is a simplified version - in practice, would need sophisticated parsing
        critical_issues = [i for i in self.issues if i.severity == ImpactLevel.CRITICAL]

        if not critical_issues:
            return None

        # For now, just return recommendations in comments
        optimized_lines = ["// OPTIMIZED QUERY - Apply these changes:"]
        for issue in critical_issues:
            optimized_lines.append(f"// {issue.issue_type}: {issue.recommendation}")

        optimized_lines.append("")
        optimized_lines.append("// Original query:")
        optimized_lines.extend(self.query_lines)

        return '\n'.join(optimized_lines)

    def _estimate_improvement(self) -> str:
        """Estimate performance improvement based on issues found."""
        if not self.issues:
            return "No optimization needed - query follows best practices"

        critical_count = sum(1 for i in self.issues if i.severity == ImpactLevel.CRITICAL)
        high_count = sum(1 for i in self.issues if i.severity == ImpactLevel.HIGH)
        medium_count = sum(1 for i in self.issues if i.severity == ImpactLevel.MEDIUM)

        if critical_count > 0:
            return f"CRITICAL: {critical_count} issue(s) may cause timeouts or auto-disable. Expected improvement: 10-100x faster"
        elif high_count > 0:
            return f"HIGH: {high_count} issue(s) causing significant performance impact. Expected improvement: 2-10x faster"
        elif medium_count > 0:
            return f"MEDIUM: {medium_count} issue(s) with moderate impact. Expected improvement: 1.5-2x faster"
        else:
            return "LOW: Minor optimizations available. Expected improvement: <1.5x"


def format_optimization_report(report: OptimizationReport) -> str:
    """Format optimization report as human-readable text."""
    lines = ["=" * 80]
    lines.append("KQL QUERY OPTIMIZATION REPORT")
    lines.append("=" * 80)
    lines.append("")

    if not report.issues:
        lines.append("✓ No issues found - query follows best practices")
        return '\n'.join(lines)

    lines.append(f"Issues Found: {len(report.issues)}")
    lines.append(f"Estimated Improvement: {report.estimated_improvement}")
    lines.append("")

    # Group by severity
    for severity in [ImpactLevel.CRITICAL, ImpactLevel.HIGH, ImpactLevel.MEDIUM, ImpactLevel.LOW]:
        severity_issues = [i for i in report.issues if i.severity == severity]
        if not severity_issues:
            continue

        lines.append(f"\n{severity.value} ISSUES ({len(severity_issues)}):")
        lines.append("-" * 80)

        for idx, issue in enumerate(severity_issues, 1):
            lines.append(f"\n{idx}. {issue.issue_type}")
            if issue.line_number:
                lines.append(f"   Line: {issue.line_number}")
            lines.append(f"   Description: {issue.description}")
            lines.append(f"   Recommendation: {issue.recommendation}")
            if issue.example_fix:
                lines.append(f"   Example Fix: {issue.example_fix}")

    if report.optimized_query:
        lines.append("\n" + "=" * 80)
        lines.append("OPTIMIZED QUERY:")
        lines.append("=" * 80)
        lines.append(report.optimized_query)

    return '\n'.join(lines)


# Example usage
if __name__ == "__main__":
    # Example query with issues
    test_query = """
SecurityEvent
| extend LowercaseAccount = tolower(Account)
| join kind=inner (
    IdentityInfo
    | project AccountName, Department
) on $left.Account == $right.AccountName
| where EventID == 4625
| where TimeGenerated > ago(1h)
| where CommandLine contains "powershell"
| sort by TimeGenerated desc
| take 100
"""

    optimizer = KQLOptimizer()
    report = optimizer.analyze_query(test_query)
    print(format_optimization_report(report))
