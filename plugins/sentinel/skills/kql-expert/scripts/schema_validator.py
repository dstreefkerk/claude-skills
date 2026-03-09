"""
KQL Schema Validator Module

Validates KQL queries against Microsoft Sentinel and M365 Defender table schemas.
Uses environments.json extracted from official Microsoft documentation.

Based on patterns from FalconForce KQLAnalyzer project.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum


class SchemaValidationSeverity(Enum):
    """Validation severity levels."""
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class SchemaValidationIssue:
    """Represents a schema validation issue."""
    severity: SchemaValidationSeverity
    category: str
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class SchemaValidationResult:
    """Schema validation result."""
    is_valid: bool
    issues: List[SchemaValidationIssue]
    referenced_tables: List[str]
    referenced_columns: List[str]
    unknown_tables: List[str]
    unknown_columns: List[str]
    environment: str


@dataclass
class TableSchema:
    """Represents a table schema with columns and types."""
    name: str
    columns: Dict[str, str]  # column_name -> type


@dataclass
class EnvironmentSchema:
    """Represents an environment's complete schema."""
    name: str
    tables: Dict[str, TableSchema]
    magic_functions: List[str] = field(default_factory=list)


class KQLSchemaValidator:
    """
    Validates KQL queries against table schemas from environments.json.

    Ported from FalconForce KQLAnalyzer patterns with Python implementation.
    """

    # Valid KQL scalar types
    VALID_TYPES = {
        'datetime', 'string', 'int', 'long', 'boolean', 'bool',
        'real', 'double', 'dynamic', 'guid', 'decimal', 'timespan'
    }

    # Built-in functions that return tables (magic functions)
    MAGIC_FUNCTIONS = {
        'FileProfile': {
            'output_columns': {
                'SHA1': 'string', 'SHA256': 'string', 'MD5': 'string',
                'FileSize': 'long', 'GlobalPrevalence': 'long',
                'GlobalFirstSeen': 'datetime', 'GlobalLastSeen': 'datetime',
                'Signer': 'string', 'Issuer': 'string', 'SignerHash': 'string',
                'IsCertificateValid': 'boolean', 'IsRootSignerMicrosoft': 'boolean',
                'SignatureState': 'string', 'IsExecutable': 'boolean',
                'ThreatName': 'string', 'Publisher': 'string',
                'SoftwareName': 'string', 'ProfileAvailability': 'string'
            }
        },
        'DeviceFromIP': {
            'output_columns': {
                'IP': 'string', 'DeviceId': 'string'
            }
        }
    }

    # Watchlist default columns
    WATCHLIST_COLUMNS = {
        '_DTItemId': 'string',
        'LastUpdatedTimeUTC': 'datetime',
        'SearchKey': 'string',
        'WatchlistItem': 'dynamic'
    }

    def __init__(self, environments_path: Optional[Union[str, Path]] = None):
        """
        Initialize validator with environments.json.

        Args:
            environments_path: Path to environments.json. If None, looks in ../references/
        """
        self.environments: Dict[str, EnvironmentSchema] = {}
        self.issues: List[SchemaValidationIssue] = []

        if environments_path is None:
            # Default path relative to this script
            script_dir = Path(__file__).parent
            env_path = script_dir.parent / 'references' / 'environments.json'
        else:
            env_path = Path(environments_path)

        self._load_environments(env_path)

    def _load_environments(self, path: Path) -> None:
        """Load environments from JSON file."""
        if not path.exists():
            raise FileNotFoundError(f"environments.json not found at {path}")

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for env_name, env_data in data.items():
            tables = {}
            for table_name, columns in env_data.get('tables', {}).items():
                tables[table_name] = TableSchema(
                    name=table_name,
                    columns={k: v for k, v in columns.items()}
                )

            self.environments[env_name] = EnvironmentSchema(
                name=env_name,
                tables=tables,
                magic_functions=env_data.get('magic_functions', [])
            )

        # Create merged m365_with_sentinel if both exist
        if 'm365' in self.environments and 'sentinel' in self.environments:
            self._create_merged_environment()

    def _create_merged_environment(self) -> None:
        """Create merged m365_with_sentinel environment."""
        m365 = self.environments['m365']
        sentinel = self.environments['sentinel']

        merged_tables = {}

        # Copy m365 tables
        for name, table in m365.tables.items():
            merged_tables[name] = TableSchema(
                name=name,
                columns=dict(table.columns)
            )

        # Add sentinel tables (no overwrite)
        for name, table in sentinel.tables.items():
            if name not in merged_tables:
                merged_tables[name] = TableSchema(
                    name=name,
                    columns=dict(table.columns)
                )

        self.environments['m365_with_sentinel'] = EnvironmentSchema(
            name='m365_with_sentinel',
            tables=merged_tables,
            magic_functions=list(m365.magic_functions)
        )

    def get_available_environments(self) -> List[str]:
        """Get list of available environments."""
        return list(self.environments.keys())

    def get_table_names(self, environment: str) -> List[str]:
        """Get all table names in an environment."""
        if environment not in self.environments:
            return []
        return list(self.environments[environment].tables.keys())

    def get_table_schema(self, environment: str, table_name: str) -> Optional[TableSchema]:
        """Get schema for a specific table."""
        if environment not in self.environments:
            return None
        return self.environments[environment].tables.get(table_name)

    def get_column_type(self, environment: str, table_name: str, column_name: str) -> Optional[str]:
        """Get type of a specific column."""
        schema = self.get_table_schema(environment, table_name)
        if schema is None:
            return None
        return schema.columns.get(column_name)

    def validate_query(
        self,
        query: str,
        environment: str = 'sentinel',
        custom_tables: Optional[Dict[str, Dict[str, str]]] = None,
        custom_watchlists: Optional[Dict[str, Dict[str, str]]] = None
    ) -> SchemaValidationResult:
        """
        Validate a KQL query against schema.

        Args:
            query: KQL query string
            environment: Environment to validate against ('m365', 'sentinel', 'm365_with_sentinel')
            custom_tables: Additional custom tables {table_name: {column: type}}
            custom_watchlists: Watchlist schemas {watchlist_name: {column: type}}

        Returns:
            SchemaValidationResult with validation details
        """
        self.issues = []

        if environment not in self.environments:
            self.issues.append(SchemaValidationIssue(
                severity=SchemaValidationSeverity.ERROR,
                category='environment',
                message=f'Unknown environment: {environment}',
                suggestion=f'Available: {", ".join(self.get_available_environments())}'
            ))
            return self._create_result(environment, [], [], [], [])

        env_schema = self.environments[environment]

        # Build complete table registry
        all_tables = dict(env_schema.tables)

        # Add custom tables
        if custom_tables:
            for table_name, columns in custom_tables.items():
                all_tables[table_name] = TableSchema(name=table_name, columns=columns)

        # Extract referenced tables and columns from query
        referenced_tables = self._extract_tables(query)
        referenced_columns = self._extract_columns(query)

        # Validate tables
        unknown_tables = []
        for table in referenced_tables:
            if table not in all_tables and not self._is_function_call(table, query):
                unknown_tables.append(table)
                self.issues.append(SchemaValidationIssue(
                    severity=SchemaValidationSeverity.ERROR,
                    category='table',
                    message=f'Unknown table: {table}',
                    suggestion=self._suggest_table(table, all_tables.keys())
                ))

        # Validate columns against known tables
        unknown_columns = []
        for col_ref in referenced_columns:
            table_name, column_name = self._parse_column_reference(col_ref, referenced_tables)
            if table_name and table_name in all_tables:
                schema = all_tables[table_name]
                if column_name not in schema.columns:
                    # Check if it's a computed column from extend
                    if not self._is_computed_column(column_name, query):
                        unknown_columns.append(f"{table_name}.{column_name}")
                        self.issues.append(SchemaValidationIssue(
                            severity=SchemaValidationSeverity.WARNING,
                            category='column',
                            message=f'Unknown column "{column_name}" in table "{table_name}"',
                            suggestion=self._suggest_column(column_name, schema.columns.keys())
                        ))

        # Validate watchlist usage
        self._validate_watchlist_usage(query, custom_watchlists)

        # Validate magic functions
        self._validate_magic_functions(query, env_schema.magic_functions)

        return self._create_result(
            environment,
            referenced_tables,
            referenced_columns,
            unknown_tables,
            unknown_columns
        )

    def _extract_tables(self, query: str) -> List[str]:
        """Extract table references from query."""
        tables = []
        lines = query.strip().split('\n')

        for line in lines:
            line = line.strip()

            # Skip comments
            if line.startswith('//'):
                continue

            # Table reference at start of query or after union
            # Pattern: TableName (starts with capital, no pipe before)
            if not line.startswith('|') and line:
                # First word might be table name
                match = re.match(r'^([A-Z][A-Za-z0-9_]+)', line)
                if match:
                    potential_table = match.group(1)
                    # Exclude KQL keywords
                    if potential_table not in {'let', 'union', 'datatable', 'print', 'range'}:
                        tables.append(potential_table)

            # Tables in union
            union_match = re.search(r'\bunion\s+(?:withsource\s*=\s*\w+\s+)?([A-Z][A-Za-z0-9_,\s]+)', line)
            if union_match:
                table_list = union_match.group(1)
                for t in re.findall(r'[A-Z][A-Za-z0-9_]+', table_list):
                    if t not in tables:
                        tables.append(t)

            # Tables in join subqueries
            join_match = re.search(r'\bjoin\s+.*?\(\s*([A-Z][A-Za-z0-9_]+)', line)
            if join_match:
                tables.append(join_match.group(1))

        return list(set(tables))

    def _extract_columns(self, query: str) -> List[str]:
        """Extract column references from query."""
        columns = set()

        # Pattern for column references in where, project, extend, summarize
        # Matches: ColumnName, Table.ColumnName
        column_pattern = re.compile(r'\b([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)\b')

        # KQL keywords and functions to exclude
        keywords = {
            'where', 'project', 'extend', 'summarize', 'join', 'on', 'by', 'in', 'and', 'or',
            'not', 'let', 'union', 'has', 'contains', 'startswith', 'endswith', 'matches',
            'regex', 'count', 'sum', 'avg', 'min', 'max', 'dcount', 'make_set', 'make_list',
            'ago', 'now', 'datetime', 'timespan', 'true', 'false', 'null', 'dynamic',
            'tostring', 'toint', 'tolong', 'todouble', 'tobool', 'todatetime', 'totimespan',
            'bin', 'floor', 'ceiling', 'round', 'strlen', 'substring', 'strcat', 'split',
            'parse', 'parse_json', 'parse_xml', 'extract', 'replace', 'tolower', 'toupper',
            'trim', 'isempty', 'isnotempty', 'isnull', 'isnotnull', 'iff', 'case', 'coalesce',
            'inner', 'outer', 'left', 'right', 'semi', 'anti', 'kind', 'hint', 'strategy',
            'broadcast', 'shuffle', 'shufflekey', 'asc', 'desc', 'nulls', 'first', 'last',
            'take', 'limit', 'top', 'sort', 'order', 'render', 'as', 'typeof', 'pack',
            'pack_all', 'bag_pack', 'mv_expand', 'mv_apply', 'evaluate', 'invoke',
            'series_decompose_anomalies', 'make_series', 'arg_min', 'arg_max', 'any',
            'countif', 'sumif', 'avgif', 'dcountif', 'percentile', 'stdev', 'variance'
        }

        for line in query.split('\n'):
            # Skip comments
            if line.strip().startswith('//'):
                continue

            for match in column_pattern.finditer(line):
                col = match.group(1)
                if col.lower() not in keywords and not col[0].isdigit():
                    columns.add(col)

        return list(columns)

    def _parse_column_reference(
        self,
        col_ref: str,
        known_tables: List[str]
    ) -> Tuple[Optional[str], str]:
        """Parse column reference to (table, column)."""
        if '.' in col_ref:
            parts = col_ref.split('.', 1)
            return parts[0], parts[1]

        # If single column name, try to find in known tables
        # Return first table that might contain it
        if known_tables:
            return known_tables[0], col_ref

        return None, col_ref

    def _is_function_call(self, name: str, query: str) -> bool:
        """Check if name is a function call rather than table."""
        # ASIM parsers
        if name.startswith('_Im_') or name.startswith('_ASim_'):
            return True

        # Check for function call pattern: name(
        pattern = rf'\b{re.escape(name)}\s*\('
        return bool(re.search(pattern, query))

    def _is_computed_column(self, column_name: str, query: str) -> bool:
        """Check if column is computed via extend."""
        # Pattern: extend ColumnName = ...
        pattern = rf'\bextend\s+.*?\b{re.escape(column_name)}\s*='
        return bool(re.search(pattern, query, re.IGNORECASE))

    def _validate_watchlist_usage(
        self,
        query: str,
        custom_watchlists: Optional[Dict[str, Dict[str, str]]]
    ) -> None:
        """Validate watchlist function usage."""
        # Find _GetWatchlist calls
        watchlist_pattern = re.compile(r'_GetWatchlist\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)')

        for match in watchlist_pattern.finditer(query):
            watchlist_name = match.group(1)

            # Check if SearchKey is used for joins
            if 'SearchKey' not in query:
                self.issues.append(SchemaValidationIssue(
                    severity=SchemaValidationSeverity.INFO,
                    category='watchlist',
                    message=f'Watchlist "{watchlist_name}" may not be using SearchKey for optimal join performance',
                    suggestion='Project SearchKey field and use it for join operations'
                ))

    def _validate_magic_functions(self, query: str, available_functions: List[str]) -> None:
        """Validate magic function usage."""
        for func_name, func_info in self.MAGIC_FUNCTIONS.items():
            if func_name in query:
                if func_name not in available_functions:
                    self.issues.append(SchemaValidationIssue(
                        severity=SchemaValidationSeverity.WARNING,
                        category='function',
                        message=f'Function "{func_name}" may not be available in selected environment',
                        suggestion='This function is typically only available in M365 Defender'
                    ))

    def _suggest_table(self, unknown: str, known_tables) -> Optional[str]:
        """Suggest similar table name."""
        known_list = list(known_tables)
        similar = self._find_similar(unknown, known_list)
        if similar:
            return f'Did you mean: {similar}?'
        return None

    def _suggest_column(self, unknown: str, known_columns) -> Optional[str]:
        """Suggest similar column name."""
        known_list = list(known_columns)
        similar = self._find_similar(unknown, known_list)
        if similar:
            return f'Did you mean: {similar}?'
        return None

    def _find_similar(self, target: str, candidates: List[str], threshold: float = 0.6) -> Optional[str]:
        """Find similar string using simple matching."""
        target_lower = target.lower()
        best_match = None
        best_score = 0

        for candidate in candidates:
            candidate_lower = candidate.lower()

            # Simple similarity: common characters / max length
            common = sum(1 for c in target_lower if c in candidate_lower)
            score = common / max(len(target_lower), len(candidate_lower))

            if score > best_score and score >= threshold:
                best_score = score
                best_match = candidate

        return best_match

    def _create_result(
        self,
        environment: str,
        referenced_tables: List[str],
        referenced_columns: List[str],
        unknown_tables: List[str],
        unknown_columns: List[str]
    ) -> SchemaValidationResult:
        """Create validation result."""
        errors = sum(1 for i in self.issues if i.severity == SchemaValidationSeverity.ERROR)

        return SchemaValidationResult(
            is_valid=(errors == 0),
            issues=self.issues,
            referenced_tables=referenced_tables,
            referenced_columns=referenced_columns,
            unknown_tables=unknown_tables,
            unknown_columns=unknown_columns,
            environment=environment
        )


def format_schema_validation_result(result: SchemaValidationResult) -> str:
    """Format validation result as human-readable text."""
    lines = ["=" * 80]
    lines.append("KQL SCHEMA VALIDATION REPORT")
    lines.append("=" * 80)
    lines.append("")

    lines.append(f"Environment: {result.environment}")
    lines.append(f"Status: {'VALID' if result.is_valid else 'INVALID'}")
    lines.append("")

    lines.append(f"Referenced Tables ({len(result.referenced_tables)}):")
    for table in result.referenced_tables:
        status = "?" if table in result.unknown_tables else "+"
        lines.append(f"  [{status}] {table}")

    if result.unknown_tables:
        lines.append(f"\nUnknown Tables: {', '.join(result.unknown_tables)}")

    if result.unknown_columns:
        lines.append(f"\nUnknown Columns: {', '.join(result.unknown_columns)}")

    if result.issues:
        lines.append(f"\nIssues ({len(result.issues)}):")
        lines.append("-" * 80)

        for severity in [SchemaValidationSeverity.ERROR, SchemaValidationSeverity.WARNING, SchemaValidationSeverity.INFO]:
            severity_issues = [i for i in result.issues if i.severity == severity]
            if severity_issues:
                lines.append(f"\n{severity.value}:")
                for issue in severity_issues:
                    lines.append(f"  - [{issue.category}] {issue.message}")
                    if issue.suggestion:
                        lines.append(f"    Suggestion: {issue.suggestion}")

    return '\n'.join(lines)


# Example usage
if __name__ == "__main__":
    # Initialize validator (will look for environments.json in ../references/)
    try:
        validator = KQLSchemaValidator()

        print("Available environments:", validator.get_available_environments())
        print()

        # Example query
        test_query = """
SecurityEvent
| where TimeGenerated > ago(1h)
| where EventID == 4625
| project TimeGenerated, Computer, AccountName, IpAddress
"""

        result = validator.validate_query(test_query, environment='sentinel')
        print(format_schema_validation_result(result))

    except FileNotFoundError as e:
        print(f"Note: {e}")
        print("Run this script from the skill directory or provide environments.json path")
