"""
KQL Analysis Module

Analyzes KQL queries to recommend severity, query frequency, trigger settings,
and generate descriptive rule names and descriptions.
"""

from typing import Dict, List, Any, Optional
import re


class KQLAnalyzer:
    """Analyze KQL queries for ARM template metadata generation."""

    # Severity mapping based on detection patterns
    SEVERITY_PATTERNS = {
        "High": [
            "brute.*force", "password.*spray", "credential.*dump", "privilege.*escalat",
            "lateral.*movement", "ransomware", "encrypt.*impact", "data.*exfiltrat",
            "malware", "backdoor", "rootkit", "persistence.*admin", "mimikatz",
            "psexec", "remote.*execution", "suspicious.*service", "domain.*admin"
        ],
        "Medium": [
            "policy.*violation", "suspicious.*behavior", "anomal", "unusual.*access",
            "failed.*authentication", "configuration.*change", "unauthorized",
            "unapproved", "non-compliant", "baseline.*deviation"
        ],
        "Low": [
            "compliance", "audit", "monitoring", "inventory", "usage.*tracking",
            "information", "baseline", "standard.*deviation"
        ]
    }

    # Frequency recommendations based on detection urgency
    FREQUENCY_PATTERNS = {
        "PT5M": [  # 5 minutes (real-time)
            "brute.*force", "active.*attack", "credential.*access", "privilege.*escalat",
            "lateral.*movement", "immediate", "critical", "ransomware"
        ],
        "PT15M": [  # 15 minutes
            "suspicious.*login", "failed.*auth", "unusual.*access", "suspicious.*process"
        ],
        "PT1H": [  # 1 hour
            "policy.*violation", "configuration.*change", "suspicious.*behavior"
        ],
        "P1D": [  # Daily
            "compliance", "audit", "trend", "baseline", "summary", "report"
        ]
    }

    def __init__(self, kql_query: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize KQL analyzer.

        Args:
            kql_query: KQL detection query
            context: Optional user context
        """
        self.kql_query = kql_query
        self.kql_lower = kql_query.lower()
        self.context = context or {}
        self.data_sources = self._extract_data_sources()

    def analyze(self) -> Dict[str, Any]:
        """
        Perform comprehensive KQL analysis.

        Returns:
            Dictionary with analysis results
        """
        return {
            "display_name": self._generate_display_name(),
            "description": self._generate_description(),
            "severity": self._determine_severity(),
            "severity_rationale": self._get_severity_rationale(),
            "query_frequency": self._determine_frequency(),
            "query_period": self._determine_period(),
            "frequency_rationale": self._get_frequency_rationale(),
            "trigger_operator": "GreaterThan",
            "trigger_threshold": self._determine_threshold(),
            "data_sources": self.data_sources
        }

    def _extract_data_sources(self) -> List[str]:
        """
        Extract data source table names from KQL query.

        Returns:
            List of table names
        """
        # Common Sentinel table patterns
        table_pattern = r'\b(' + '|'.join([
            'SigninLogs', 'AuditLogs', 'AADNonInteractiveUserSignInLogs',
            'AADServicePrincipalSignInLogs', 'DeviceEvents', 'DeviceFileEvents',
            'DeviceNetworkEvents', 'DeviceProcessEvents', 'DeviceRegistryEvents',
            'DeviceLogonEvents', 'SecurityEvent', 'WindowsEvent', 'Syslog',
            'CommonSecurityLog', 'AzureActivity', 'AzureDiagnostics',
            'OfficeActivity', 'AWSCloudTrail', 'AlertEvidence', 'EmailEvents',
            'EmailAttachmentInfo', 'EmailUrlInfo', 'IdentityInfo'
        ]) + r')\b'

        tables = re.findall(table_pattern, self.kql_query, re.IGNORECASE)
        return list(set(tables))

    def _generate_display_name(self) -> str:
        """
        Generate descriptive rule display name from query analysis.

        Returns:
            Display name string
        """
        # Check for user override
        if self.context.get("display_name"):
            return self.context["display_name"]

        # Detection pattern to name mapping
        patterns = {
            r"brute.*force|failed.*login.*count": "Multiple Failed Sign-In Attempts",
            r"password.*spray": "Password Spray Attack Detection",
            r"privilege.*escalat": "Privilege Escalation Attempt",
            r"lateral.*movement|psexec|remote.*exec": "Lateral Movement Activity",
            r"service.*creat": "Suspicious Service Creation",
            r"scheduled.*task": "Suspicious Scheduled Task Creation",
            r"registry.*run|autostart": "Registry Persistence Mechanism",
            r"powershell.*encoded|hidden.*window": "Suspicious PowerShell Execution",
            r"data.*exfiltrat|large.*transfer": "Potential Data Exfiltration",
            r"ransomware|encrypt.*file": "Ransomware Activity Detection",
            r"credential.*dump|mimikatz": "Credential Dumping Attempt",
            r"rdp.*connection": "Remote Desktop Protocol Access",
            r"suspicious.*ip|malicious.*domain": "Connection to Suspicious Destination",
            r"log.*clear|event.*deletion": "Security Log Tampering",
            r"disable.*antivirus|security.*disable": "Security Tool Disablement",
            r"file.*temp.*download": "Suspicious File Download to Temp Directory",
            r"admin.*account|privileged.*account": "Privileged Account Activity",
            r"mfa.*bypass|authentication.*skip": "Multi-Factor Authentication Bypass"
        }

        for pattern, name in patterns.items():
            if re.search(pattern, self.kql_lower):
                # Add data source context if available
                if self.data_sources:
                    primary_source = self.data_sources[0]
                    if "Signin" in primary_source or "AAD" in primary_source:
                        return f"{name} - Azure AD"
                    elif "Device" in primary_source:
                        return f"{name} - Endpoint"
                    elif "Office" in primary_source:
                        return f"{name} - Office 365"
                return name

        # Generic name based on data source
        if self.data_sources:
            source = self.data_sources[0]
            if "Signin" in source:
                return "Azure AD Sign-In Anomaly Detection"
            elif "Device" in source:
                return "Endpoint Security Event Detection"
            elif "Security" in source:
                return "Security Event Detection"
            elif "Office" in source:
                return "Office 365 Activity Detection"

        return "Custom Security Detection Rule"

    def _generate_description(self) -> str:
        """
        Generate rule description from query analysis.

        Returns:
            Description string
        """
        # Check for user override
        if self.context.get("description"):
            return self.context["description"]

        # Build description based on detected patterns
        description_parts = []

        # Detection purpose
        if re.search(r"brute.*force|failed.*login.*count", self.kql_lower):
            description_parts.append("Detects multiple failed authentication attempts from a single source")
        elif re.search(r"password.*spray", self.kql_lower):
            description_parts.append("Identifies password spray attacks across multiple accounts")
        elif re.search(r"privilege.*escalat", self.kql_lower):
            description_parts.append("Detects attempts to escalate privileges on systems")
        elif re.search(r"lateral.*movement", self.kql_lower):
            description_parts.append("Identifies lateral movement activities across the network")
        elif re.search(r"data.*exfiltrat", self.kql_lower):
            description_parts.append("Detects potential data exfiltration activities")
        else:
            description_parts.append("Detects suspicious security events")

        # Add data source context
        if self.data_sources:
            sources_str = ", ".join(self.data_sources[:2])
            description_parts.append(f"by analyzing {sources_str} logs")

        # Add threshold context if present
        threshold_match = re.search(r'where\s+\w+\s*>=?\s*(\d+)', self.kql_query, re.IGNORECASE)
        if threshold_match:
            threshold = threshold_match.group(1)
            description_parts.append(f"with a threshold of {threshold} events")

        return ". ".join(description_parts) + "."

    def _determine_severity(self) -> str:
        """
        Determine appropriate severity level.

        Returns:
            Severity string (High/Medium/Low/Informational)
        """
        # Check for user override
        if self.context.get("severity"):
            return self.context["severity"]

        # Check patterns for severity
        for severity, patterns in self.SEVERITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, self.kql_lower):
                    return severity

        # Default to Medium if no clear pattern
        return "Medium"

    def _get_severity_rationale(self) -> str:
        """
        Get rationale for severity assignment.

        Returns:
            Rationale string
        """
        severity = self._determine_severity()

        if severity == "High":
            return "High severity assigned due to indicators of active attack or critical security threat"
        elif severity == "Medium":
            return "Medium severity assigned due to suspicious behavior requiring investigation"
        elif severity == "Low":
            return "Low severity assigned for compliance monitoring and baseline tracking"
        else:
            return "Informational severity for audit and tracking purposes"

    def _determine_frequency(self) -> str:
        """
        Determine query frequency (how often to run the query).

        Returns:
            ISO 8601 duration string
        """
        # Check for user override
        if self.context.get("query_frequency"):
            return self.context["query_frequency"]

        # Check patterns for frequency
        for frequency, patterns in self.FREQUENCY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, self.kql_lower):
                    return frequency

        # Default based on severity
        severity = self._determine_severity()
        if severity == "High":
            return "PT5M"
        elif severity == "Medium":
            return "PT1H"
        else:
            return "P1D"

    def _determine_period(self) -> str:
        """
        Determine query period (lookback window).

        IMPORTANT: queryPeriod should ALWAYS be longer than queryFrequency
        to account for data ingestion delays. This prevents missed alerts
        when data arrives late.

        Returns:
            ISO 8601 duration string
        """
        # Check for user override
        if self.context.get("query_period"):
            return self.context["query_period"]

        # Extract time window from query if present
        time_pattern = re.search(r'TimeGenerated\s*>\s*ago\((\d+)([mhd])\)', self.kql_query, re.IGNORECASE)
        if time_pattern:
            value = int(time_pattern.group(1))
            unit = time_pattern.group(2).lower()

            if unit == 'm':
                return f"PT{value}M"
            elif unit == 'h':
                return f"PT{value}H"
            elif unit == 'd':
                return f"P{value}D"

        # Set period LONGER than frequency to handle ingestion lag
        # This is critical to prevent missed alerts from late-arriving data
        frequency = self._determine_frequency()

        # Ingestion lag buffer mappings (frequency → period with buffer)
        if frequency == "PT5M":
            return "PT10M"   # +5 min buffer for ingestion delay
        elif frequency == "PT15M":
            return "PT30M"   # +15 min buffer
        elif frequency == "PT1H":
            return "PT2H"    # +1 hour buffer
        elif frequency == "P1D":
            return "P1D"     # Daily queries use explicit TimeGenerated filter
        else:
            return frequency

    def _get_frequency_rationale(self) -> str:
        """
        Get rationale for frequency selection.

        Returns:
            Rationale string
        """
        frequency = self._determine_frequency()

        if frequency == "PT5M":
            return "5-minute frequency for real-time detection of active threats"
        elif frequency == "PT15M":
            return "15-minute frequency for near real-time suspicious activity detection"
        elif frequency == "PT1H":
            return "Hourly frequency for behavioral pattern detection"
        elif frequency == "P1D":
            return "Daily frequency for trend analysis and compliance monitoring"
        else:
            return f"Custom frequency: {frequency}"

    def _determine_threshold(self) -> int:
        """
        Determine trigger threshold.

        Returns:
            Threshold integer
        """
        # Check for user override
        if self.context.get("trigger_threshold") is not None:
            return self.context["trigger_threshold"]

        # If query already has aggregation/counting, threshold is 0
        if re.search(r'\bcount\(|\bsum\(|\bsummarize\b', self.kql_query, re.IGNORECASE):
            return 0

        # Otherwise, trigger on any result
        return 0
