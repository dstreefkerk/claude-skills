"""
MITRE ATT&CK Mapping Module

Intelligent MITRE ATT&CK framework mapping based on KQL query patterns
and detection context. Automatically suggests tactics, techniques, and sub-techniques.
"""

from typing import Dict, List, Any, Optional
import re


class MitreAttackMapper:
    """Maps detection patterns to MITRE ATT&CK tactics and techniques."""

    # MITRE ATT&CK mapping database
    ATTACK_PATTERNS = {
        # Authentication & Credential Patterns
        "failed_login": {
            "tactics": ["InitialAccess", "CredentialAccess"],
            "techniques": ["T1078", "T1110"],
            "sub_techniques": ["T1110.001", "T1110.003"],
            "keywords": ["failed", "signin", "login", "authentication", "logon", "ResultType", "FailedAttempts"]
        },
        "brute_force": {
            "tactics": ["CredentialAccess"],
            "techniques": ["T1110"],
            "sub_techniques": ["T1110.001", "T1110.003", "T1110.004"],
            "keywords": ["brute", "multiple.*attempts", "failed.*login", "password.*spray", "count.*fail"]
        },
        "mfa_bypass": {
            "tactics": ["CredentialAccess"],
            "techniques": ["T1556"],
            "sub_techniques": ["T1556.006"],
            "keywords": ["mfa", "multi-factor", "2fa", "authentication.*bypass", "StrongAuthenticationRequirement"]
        },
        "privileged_account": {
            "tactics": ["PrivilegeEscalation", "InitialAccess"],
            "techniques": ["T1078"],
            "sub_techniques": ["T1078.002", "T1078.004"],
            "keywords": ["admin", "privileged", "elevated", "domain.*admin", "root", "sudo"]
        },

        # Persistence Patterns
        "service_creation": {
            "tactics": ["Persistence", "PrivilegeEscalation"],
            "techniques": ["T1543"],
            "sub_techniques": ["T1543.003"],
            "keywords": ["service.*creat", "sc.*create", "New-Service", "ServiceFileName"]
        },
        "scheduled_task": {
            "tactics": ["Persistence", "PrivilegeEscalation"],
            "techniques": ["T1053"],
            "sub_techniques": ["T1053.005"],
            "keywords": ["schtasks", "scheduled.*task", "Register-ScheduledTask", "TaskScheduler"]
        },
        "registry_autostart": {
            "tactics": ["Persistence", "PrivilegeEscalation"],
            "techniques": ["T1547"],
            "sub_techniques": ["T1547.001"],
            "keywords": ["registry.*run", "HKLM.*Run", "HKCU.*Run", "CurrentVersion\\\\Run"]
        },
        "startup_folder": {
            "tactics": ["Persistence"],
            "techniques": ["T1547"],
            "sub_techniques": ["T1547.001"],
            "keywords": ["startup.*folder", "\\\\Startup\\\\", "shell:startup"]
        },

        # Lateral Movement Patterns
        "remote_powershell": {
            "tactics": ["LateralMovement", "Execution"],
            "techniques": ["T1021", "T1059"],
            "sub_techniques": ["T1021.006", "T1059.001"],
            "keywords": ["winrm", "powershell.*remoting", "Invoke-Command", "Enter-PSSession"]
        },
        "rdp_connection": {
            "tactics": ["LateralMovement"],
            "techniques": ["T1021"],
            "sub_techniques": ["T1021.001"],
            "keywords": ["rdp", "remote.*desktop", "mstsc", "TerminalServices", "LogonType.*10"]
        },
        "psexec": {
            "tactics": ["LateralMovement", "Execution"],
            "techniques": ["T1570", "T1021"],
            "sub_techniques": ["T1021.002"],
            "keywords": ["psexec", "paexec", "PSEXESVC", "ADMIN\\$"]
        },
        "smb_admin": {
            "tactics": ["LateralMovement"],
            "techniques": ["T1021"],
            "sub_techniques": ["T1021.002"],
            "keywords": ["smb", "\\\\\\\\.*\\\\C\\$", "ADMIN\\$", "IPC\\$"]
        },

        # Execution Patterns
        "powershell_execution": {
            "tactics": ["Execution"],
            "techniques": ["T1059"],
            "sub_techniques": ["T1059.001"],
            "keywords": ["powershell", "pwsh", "encoded.*command", "-enc", "-w.*hidden"]
        },
        "command_shell": {
            "tactics": ["Execution"],
            "techniques": ["T1059"],
            "sub_techniques": ["T1059.003"],
            "keywords": ["cmd.exe", "command.*shell", "/c ", "bat$", "CommandLine.*cmd"]
        },
        "wmi_execution": {
            "tactics": ["Execution"],
            "techniques": ["T1047"],
            "sub_techniques": [],
            "keywords": ["wmic", "Win32_Process", "wmiprvse", "WmiPrvSE.exe"]
        },

        # Defense Evasion Patterns
        "log_deletion": {
            "tactics": ["DefenseEvasion"],
            "techniques": ["T1070"],
            "sub_techniques": ["T1070.001"],
            "keywords": ["wevtutil", "clear.*log", "Remove-EventLog", "EventLog.*cleared"]
        },
        "disable_security": {
            "tactics": ["DefenseEvasion"],
            "techniques": ["T1562"],
            "sub_techniques": ["T1562.001", "T1562.004"],
            "keywords": ["disable.*antivirus", "Stop-Service.*Defender", "tamper.*protection", "Set-MpPreference"]
        },
        "process_injection": {
            "tactics": ["DefenseEvasion", "PrivilegeEscalation"],
            "techniques": ["T1055"],
            "sub_techniques": ["T1055.001", "T1055.002"],
            "keywords": ["inject", "VirtualAllocEx", "WriteProcessMemory", "CreateRemoteThread"]
        },

        # Exfiltration Patterns
        "data_transfer": {
            "tactics": ["Exfiltration"],
            "techniques": ["T1041"],
            "sub_techniques": [],
            "keywords": ["upload", "exfil", "data.*transfer", "large.*outbound", "BytesSent"]
        },
        "cloud_storage": {
            "tactics": ["Exfiltration"],
            "techniques": ["T1567"],
            "sub_techniques": ["T1567.002"],
            "keywords": ["dropbox", "onedrive", "google.*drive", "box.com", "cloud.*storage"]
        },
        "dns_tunneling": {
            "tactics": ["Exfiltration", "CommandAndControl"],
            "techniques": ["T1048", "T1071"],
            "sub_techniques": ["T1048.003", "T1071.004"],
            "keywords": ["dns.*tunnel", "dns.*query.*length", "unusual.*dns", "base64.*dns"]
        },

        # Command & Control Patterns
        "beacon_activity": {
            "tactics": ["CommandAndControl"],
            "techniques": ["T1071"],
            "sub_techniques": ["T1071.001"],
            "keywords": ["beacon", "c2", "command.*control", "periodic.*connection", "regular.*interval"]
        },
        "suspicious_network": {
            "tactics": ["CommandAndControl"],
            "techniques": ["T1071"],
            "sub_techniques": ["T1071.001"],
            "keywords": ["suspicious.*ip", "malicious.*domain", "unusual.*port", "RemoteIP", "DestinationIP"]
        },

        # Discovery Patterns
        "network_scan": {
            "tactics": ["Discovery"],
            "techniques": ["T1046"],
            "sub_techniques": [],
            "keywords": ["port.*scan", "nmap", "network.*discovery", "masscan"]
        },
        "account_discovery": {
            "tactics": ["Discovery"],
            "techniques": ["T1087"],
            "sub_techniques": ["T1087.001", "T1087.002"],
            "keywords": ["net.*user", "Get-ADUser", "whoami", "account.*enum"]
        },

        # Privilege Escalation Patterns
        "sudo_abuse": {
            "tactics": ["PrivilegeEscalation"],
            "techniques": ["T1548"],
            "sub_techniques": ["T1548.003"],
            "keywords": ["sudo", "su -", "privilege.*escalat", "elevation"]
        },
        "uac_bypass": {
            "tactics": ["PrivilegeEscalation", "DefenseEvasion"],
            "techniques": ["T1548"],
            "sub_techniques": ["T1548.002"],
            "keywords": ["uac.*bypass", "eventvwr", "fodhelper", "User.*Account.*Control"]
        },

        # Collection Patterns
        "clipboard_data": {
            "tactics": ["Collection"],
            "techniques": ["T1115"],
            "sub_techniques": [],
            "keywords": ["clipboard", "Get-Clipboard", "clip.exe"]
        },
        "screen_capture": {
            "tactics": ["Collection"],
            "techniques": ["T1113"],
            "sub_techniques": [],
            "keywords": ["screenshot", "screen.*capture", "Print.*Screen", "snapshot"]
        },

        # Impact Patterns
        "ransomware": {
            "tactics": ["Impact"],
            "techniques": ["T1486"],
            "sub_techniques": [],
            "keywords": ["encrypt", "ransom", "\\.locked", "\\.crypt", "file.*encryption"]
        },
        "data_destruction": {
            "tactics": ["Impact"],
            "techniques": ["T1485"],
            "sub_techniques": [],
            "keywords": ["delete", "destroy", "wipe", "shred", "Remove-Item.*-Recurse"]
        }
    }

    def __init__(self, kql_query: str, context: Optional[Dict[str, Any]] = None, analysis: Optional[Dict[str, Any]] = None):
        """
        Initialize MITRE mapper.

        Args:
            kql_query: KQL detection query
            context: Optional user context
            analysis: Optional KQL analysis results
        """
        self.kql_query = kql_query.lower()
        self.context = context or {}
        self.analysis = analysis or {}

    def get_mappings(self) -> Dict[str, Any]:
        """
        Generate MITRE ATT&CK mappings based on query patterns.

        Returns:
            Dictionary with tactics, techniques, sub_techniques, and rationale
        """
        # Check for user overrides
        if self.context.get("mitre_tactics") and self.context.get("mitre_techniques"):
            return {
                "tactics": self.context["mitre_tactics"],
                "techniques": self.context["mitre_techniques"],
                "sub_techniques": self.context.get("mitre_sub_techniques", []),
                "rationale": "User-specified MITRE mappings"
            }

        # Auto-detect patterns
        detected_patterns = self._detect_patterns()

        if not detected_patterns:
            return {
                "tactics": [],
                "techniques": [],
                "sub_techniques": [],
                "rationale": "No clear MITRE patterns detected. Manual review recommended."
            }

        # Aggregate tactics and techniques
        tactics = set()
        techniques = set()
        sub_techniques = set()
        pattern_names = []

        for pattern_name in detected_patterns:
            pattern = self.ATTACK_PATTERNS[pattern_name]
            tactics.update(pattern["tactics"])
            techniques.update(pattern["techniques"])
            sub_techniques.update(pattern["sub_techniques"])
            pattern_names.append(pattern_name.replace("_", " ").title())

        return {
            "tactics": sorted(list(tactics)),
            "techniques": sorted(list(techniques)),
            "sub_techniques": sorted(list(sub_techniques)),
            "rationale": f"Auto-detected patterns: {', '.join(pattern_names)}"
        }

    def _detect_patterns(self) -> List[str]:
        """
        Detect attack patterns in KQL query.

        Returns:
            List of detected pattern names
        """
        detected = []

        for pattern_name, pattern_data in self.ATTACK_PATTERNS.items():
            # Check if any keywords match the query
            for keyword in pattern_data["keywords"]:
                if re.search(keyword, self.kql_query, re.IGNORECASE):
                    detected.append(pattern_name)
                    break  # Avoid duplicate detection for same pattern

        return detected

    def get_technique_description(self, technique_id: str) -> str:
        """
        Get human-readable description of MITRE technique.

        Args:
            technique_id: MITRE technique ID (e.g., "T1078")

        Returns:
            Description string
        """
        descriptions = {
            "T1078": "Valid Accounts",
            "T1110": "Brute Force",
            "T1110.001": "Password Guessing",
            "T1110.003": "Password Spraying",
            "T1110.004": "Credential Stuffing",
            "T1556": "Modify Authentication Process",
            "T1556.006": "Multi-Factor Authentication",
            "T1543": "Create or Modify System Process",
            "T1543.003": "Windows Service",
            "T1053": "Scheduled Task/Job",
            "T1053.005": "Scheduled Task",
            "T1547": "Boot or Logon Autostart Execution",
            "T1547.001": "Registry Run Keys / Startup Folder",
            "T1021": "Remote Services",
            "T1021.001": "Remote Desktop Protocol",
            "T1021.002": "SMB/Windows Admin Shares",
            "T1021.006": "Windows Remote Management",
            "T1059": "Command and Scripting Interpreter",
            "T1059.001": "PowerShell",
            "T1059.003": "Windows Command Shell",
            "T1047": "Windows Management Instrumentation",
            "T1070": "Indicator Removal",
            "T1070.001": "Clear Windows Event Logs",
            "T1562": "Impair Defenses",
            "T1562.001": "Disable or Modify Tools",
            "T1562.004": "Disable or Modify System Firewall",
            "T1055": "Process Injection",
            "T1055.001": "Dynamic-link Library Injection",
            "T1055.002": "Portable Executable Injection",
            "T1041": "Exfiltration Over C2 Channel",
            "T1567": "Exfiltration Over Web Service",
            "T1567.002": "Exfiltration to Cloud Storage",
            "T1048": "Exfiltration Over Alternative Protocol",
            "T1048.003": "Exfiltration Over Unencrypted Non-C2 Protocol",
            "T1071": "Application Layer Protocol",
            "T1071.001": "Web Protocols",
            "T1071.004": "DNS",
            "T1046": "Network Service Discovery",
            "T1087": "Account Discovery",
            "T1087.001": "Local Account",
            "T1087.002": "Domain Account",
            "T1548": "Abuse Elevation Control Mechanism",
            "T1548.002": "Bypass User Account Control",
            "T1548.003": "Sudo and Sudo Caching",
            "T1115": "Clipboard Data",
            "T1113": "Screen Capture",
            "T1486": "Data Encrypted for Impact",
            "T1485": "Data Destruction",
            "T1570": "Lateral Tool Transfer"
        }

        return descriptions.get(technique_id, technique_id)
