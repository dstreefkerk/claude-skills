# MITRE ATT&CK Mapping Reference

Intelligence for auto-mapping MITRE tactics and techniques based on detection patterns.

---

## Supported Tactics

| Tactic | Description |
|--------|-------------|
| Reconnaissance | Gathering information about targets |
| ResourceDevelopment | Preparing attack infrastructure |
| InitialAccess | Gaining initial foothold |
| Execution | Running malicious code |
| Persistence | Maintaining access |
| PrivilegeEscalation | Gaining higher privileges |
| DefenseEvasion | Avoiding detection |
| CredentialAccess | Stealing credentials |
| Discovery | Mapping the environment |
| LateralMovement | Moving through network |
| Collection | Gathering target data |
| CommandAndControl | Communicating with implants |
| Exfiltration | Stealing data out |
| Impact | Disrupting operations |

---

## Detection Pattern Mappings

### Authentication/Credential Patterns

| Detection Pattern | Tactics | Techniques |
|-------------------|---------|------------|
| Failed logins, brute force | InitialAccess, CredentialAccess | T1078, T1110 |
| MFA bypass attempts | CredentialAccess | T1556 |
| Privileged account abuse | PrivilegeEscalation | T1078.002 |
| Password spray | CredentialAccess | T1110.003 |
| Credential dumping | CredentialAccess | T1003 |

### Persistence Patterns

| Detection Pattern | Tactics | Techniques |
|-------------------|---------|------------|
| Service creation | Persistence | T1543, T1543.003 |
| Scheduled tasks | Persistence | T1053 |
| Registry modifications | Persistence | T1547 |
| Startup folder changes | Persistence | T1547.001 |
| Account creation | Persistence | T1136 |

### Lateral Movement Patterns

| Detection Pattern | Tactics | Techniques |
|-------------------|---------|------------|
| Remote PowerShell | LateralMovement | T1021.006 |
| RDP connections | LateralMovement | T1021.001 |
| PsExec activity | LateralMovement | T1570 |
| WMI remote execution | LateralMovement | T1021.003 |
| SSH lateral movement | LateralMovement | T1021.004 |

### Exfiltration Patterns

| Detection Pattern | Tactics | Techniques |
|-------------------|---------|------------|
| Large data transfers | Exfiltration | T1041 |
| Cloud storage uploads | Exfiltration | T1567 |
| DNS tunneling | Exfiltration | T1048 |
| Email exfiltration | Exfiltration | T1048.003 |

### Command & Control Patterns

| Detection Pattern | Tactics | Techniques |
|-------------------|---------|------------|
| Beacon activity | CommandAndControl | T1071 |
| Suspicious network connections | CommandAndControl | T1095 |
| Encoded commands | CommandAndControl | T1132 |
| Web protocols C2 | CommandAndControl | T1071.001 |

### Execution Patterns

| Detection Pattern | Tactics | Techniques |
|-------------------|---------|------------|
| PowerShell execution | Execution | T1059.001 |
| Script execution | Execution | T1059 |
| Malicious macros | Execution | T1204.002 |
| WMI execution | Execution | T1047 |

### Defense Evasion Patterns

| Detection Pattern | Tactics | Techniques |
|-------------------|---------|------------|
| Log clearing | DefenseEvasion | T1070 |
| Process injection | DefenseEvasion | T1055 |
| Timestomping | DefenseEvasion | T1070.006 |
| Disabling security tools | DefenseEvasion | T1562 |

---

## Common Technique Reference

| Technique ID | Name | Common Detections |
|--------------|------|-------------------|
| T1078 | Valid Accounts | Anomalous login patterns |
| T1078.004 | Cloud Accounts | Unusual cloud sign-ins |
| T1110 | Brute Force | Multiple failed logins |
| T1110.003 | Password Spray | Low-volume distributed auth failures |
| T1003 | OS Credential Dumping | LSASS access, SAM registry |
| T1543 | Create/Modify System Process | Service installations |
| T1543.003 | Windows Service | sc.exe, New-Service |
| T1053 | Scheduled Task/Job | Task scheduler events |
| T1547 | Boot/Logon Autostart | Registry run keys |
| T1059 | Command and Scripting | Script interpreter processes |
| T1059.001 | PowerShell | PowerShell.exe execution |
| T1021 | Remote Services | RDP, SSH, WinRM connections |
| T1070 | Indicator Removal | Security log clearing |
| T1055 | Process Injection | Cross-process memory access |
| T1486 | Data Encrypted for Impact | Mass file encryption |
| T1566 | Phishing | Suspicious email attachments |

---

## Severity Inference by Tactic

| Tactic(s) | Typical Severity |
|-----------|------------------|
| CredentialAccess, Exfiltration | High |
| PrivilegeEscalation, LateralMovement | High |
| Execution (with malware indicators) | High |
| Persistence, DefenseEvasion | Medium-High |
| InitialAccess, Discovery | Medium |
| Reconnaissance | Low-Medium |
| Collection (without exfiltration) | Medium |
