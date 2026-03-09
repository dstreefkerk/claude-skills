"""
KQL Query Patterns Module

Provides reusable query templates and patterns for common Microsoft Sentinel
scenarios including analytics rules, threat hunting, ASIM normalization,
and performance-optimized queries.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class QueryPattern:
    """Represents a reusable KQL query pattern."""
    name: str
    description: str
    category: str
    template: str
    parameters: Dict[str, str]
    mitre_tactics: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)


class KQLPatterns:
    """Collection of KQL query patterns and templates."""

    def __init__(self):
        self.patterns = self._initialize_patterns()

    def _initialize_patterns(self) -> Dict[str, QueryPattern]:
        """Initialize all query patterns."""
        patterns = {}

        # Analytics Rule Patterns
        patterns.update(self._analytics_rule_patterns())

        # Threat Hunting Patterns
        patterns.update(self._threat_hunting_patterns())

        # ASIM Patterns
        patterns.update(self._asim_patterns())

        # Performance Optimization Patterns
        patterns.update(self._optimization_patterns())

        return patterns

    def _analytics_rule_patterns(self) -> Dict[str, QueryPattern]:
        """Analytics rule templates."""
        return {
            'brute_force_auth': QueryPattern(
                name='Brute Force Authentication Detection',
                description='Detect brute force authentication attempts using ASIM normalization',
                category='analytics_rule',
                template='''// Brute Force Authentication Detection (ASIM)
let threshold = {threshold};
let timeframe = {timeframe};
_Im_Authentication(
    starttime=ago(timeframe),
    endtime=now(),
    eventresult='Failure'
)
| summarize
    FailedAttempts = count(),
    TargetAccounts = make_set(TargetUsername),
    FirstAttempt = min(TimeGenerated),
    LastAttempt = max(TimeGenerated)
    by SrcIpAddr, bin(TimeGenerated, 5m)
| where FailedAttempts >= threshold
| extend
    AttackDuration = LastAttempt - FirstAttempt,
    UniqueAccounts = array_length(TargetAccounts)
| project
    TimeGenerated,
    SrcIpAddr,
    FailedAttempts,
    UniqueAccounts,
    AttackDuration,
    FirstAttempt,
    LastAttempt,
    TargetAccounts''',
                parameters={
                    'threshold': 'Number of failed attempts (e.g., 10)',
                    'timeframe': 'Time window (e.g., 1h, 24h)'
                },
                mitre_tactics=['Credential Access'],
                data_sources=['ASIM Authentication']
            ),

            'suspicious_process_execution': QueryPattern(
                name='Suspicious Process Execution',
                description='Detect suspicious process execution patterns',
                category='analytics_rule',
                template='''// Suspicious Process Execution Detection
let timeframe = {timeframe};
let suspiciousProcesses = dynamic({process_list});
let suspiciousCommandPatterns = dynamic({command_patterns});
DeviceProcessEvents
| where TimeGenerated > ago(timeframe)
| where FileName in~ (suspiciousProcesses)
    or ProcessCommandLine has_any (suspiciousCommandPatterns)
| extend
    ProcessHash = SHA256,
    ParentProcessName = InitiatingProcessFileName
| join kind=leftouter (
    DeviceInfo
    | where TimeGenerated > ago(timeframe)
    | project DeviceId, DeviceName, OSPlatform, IsAzureADJoined
) on DeviceId
| project
    TimeGenerated,
    DeviceName,
    AccountName,
    FileName,
    ProcessCommandLine,
    ProcessHash,
    ParentProcessName,
    InitiatingProcessCommandLine,
    OSPlatform,
    IsAzureADJoined''',
                parameters={
                    'timeframe': 'Time window (e.g., 1h)',
                    'process_list': '["powershell.exe", "cmd.exe", "wmic.exe", "rundll32.exe"]',
                    'command_patterns': '["IEX", "DownloadString", "Invoke-Expression", "bypass"]'
                },
                mitre_tactics=['Execution', 'Defense Evasion'],
                data_sources=['DeviceProcessEvents']
            ),

            'impossible_travel': QueryPattern(
                name='Impossible Travel Detection',
                description='Detect geographically impossible travel patterns',
                category='analytics_rule',
                template='''// Impossible Travel Detection
let timeframe = {timeframe};
let minDistanceKm = {min_distance};
let maxTravelTimeHours = {max_time};
SigninLogs
| where TimeGenerated > ago(timeframe)
| where ResultType == 0  // Successful sign-ins only
| where isnotempty(Location)
| project
    TimeGenerated,
    UserPrincipalName,
    IPAddress,
    Location,
    City = LocationDetails.city,
    State = LocationDetails.state,
    Country = LocationDetails.countryOrRegion,
    Latitude = toreal(LocationDetails.geoCoordinates.latitude),
    Longitude = toreal(LocationDetails.geoCoordinates.longitude)
| where isnotempty(Latitude) and isnotempty(Longitude)
| order by UserPrincipalName, TimeGenerated asc
| serialize
| extend
    PrevTime = prev(TimeGenerated, 1),
    PrevLocation = prev(Location, 1),
    PrevLat = prev(Latitude, 1),
    PrevLong = prev(Longitude, 1),
    PrevUser = prev(UserPrincipalName, 1)
| where UserPrincipalName == PrevUser
| extend TimeDiffHours = datetime_diff('hour', TimeGenerated, PrevTime)
| where TimeDiffHours > 0 and TimeDiffHours <= maxTravelTimeHours
| extend DistanceKm = geo_distance_2points(PrevLong, PrevLat, Longitude, Latitude) / 1000
| where DistanceKm >= minDistanceKm
| extend RequiredSpeedKmH = DistanceKm / TimeDiffHours
| where RequiredSpeedKmH > 800  // Faster than commercial flight
| project
    TimeGenerated,
    UserPrincipalName,
    IPAddress,
    CurrentLocation = Location,
    PreviousLocation = PrevLocation,
    DistanceKm = round(DistanceKm, 2),
    TimeDiffHours = round(TimeDiffHours, 2),
    RequiredSpeedKmH = round(RequiredSpeedKmH, 2)''',
                parameters={
                    'timeframe': 'Time window (e.g., 7d)',
                    'min_distance': 'Minimum distance in km (e.g., 500)',
                    'max_time': 'Maximum time between logins in hours (e.g., 24)'
                },
                mitre_tactics=['Initial Access', 'Credential Access'],
                data_sources=['SigninLogs']
            )
        }

    def _threat_hunting_patterns(self) -> Dict[str, QueryPattern]:
        """Threat hunting query templates."""
        return {
            'ioc_threat_intel': QueryPattern(
                name='Threat Intelligence IoC Matching',
                description='Match network activity against threat intelligence indicators',
                category='threat_hunting',
                template='''// Threat Intelligence IoC Detection
let TI_lookback = {ti_lookback};
let Query_lookback = {query_lookback};
let ThreatIntel = ThreatIntelligenceIndicator
    | where TimeGenerated >= ago(TI_lookback)
    | where ExpirationDateTime > now() and Active == true
    | where isnotempty(NetworkIP) or isnotempty(NetworkSourceIP) or isnotempty(NetworkDestinationIP)
    | extend TI_ipEntity = coalesce(NetworkIP, NetworkDestinationIP, NetworkSourceIP)
    | summarize arg_max(TimeGenerated, *) by IndicatorId
    | project TI_ipEntity, Description, ThreatType, ConfidenceScore, ThreatSeverity;
DeviceNetworkEvents
| where TimeGenerated >= ago(Query_lookback)
| where ActionType == "ConnectionSuccess"
| extend DeviceIP = RemoteIP
| join kind=inner (ThreatIntel) on $left.DeviceIP == $right.TI_ipEntity
| project
    TimeGenerated,
    DeviceName,
    RemoteIP,
    RemoteUrl,
    RemotePort,
    ThreatType,
    Description,
    ConfidenceScore,
    ThreatSeverity,
    InitiatingProcessFileName,
    InitiatingProcessCommandLine
| sort by ConfidenceScore desc''',
                parameters={
                    'ti_lookback': 'Threat intel age (e.g., 14d)',
                    'query_lookback': 'Event search window (e.g., 1h)'
                },
                mitre_tactics=['Command and Control'],
                data_sources=['ThreatIntelligenceIndicator', 'DeviceNetworkEvents']
            ),

            'lateral_movement': QueryPattern(
                name='Lateral Movement Detection',
                description='Detect lateral movement via remote services',
                category='threat_hunting',
                template='''// Lateral Movement Detection
let timeframe = {timeframe};
let lateralMovementPorts = dynamic([5985, 5986, 3389, 445, 135]);  // WinRM, RDP, SMB, RPC
DeviceNetworkEvents
| where TimeGenerated > ago(timeframe)
| where RemotePort in (lateralMovementPorts)
| where ActionType == "ConnectionSuccess"
| summarize
    ConnectionCount = count(),
    TargetDevices = make_set(RemoteIP),
    TargetCount = dcount(RemoteIP),
    Ports = make_set(RemotePort),
    FirstSeen = min(TimeGenerated),
    LastSeen = max(TimeGenerated)
    by DeviceName, InitiatingProcessFileName, bin(TimeGenerated, 1h)
| where TargetCount >= {target_threshold}  // Multiple targets suggest lateral movement
| extend TimeWindow = LastSeen - FirstSeen
| project
    TimeGenerated,
    DeviceName,
    InitiatingProcessFileName,
    TargetCount,
    ConnectionCount,
    TargetDevices,
    Ports,
    TimeWindow
| sort by TargetCount desc''',
                parameters={
                    'timeframe': 'Time window (e.g., 7d)',
                    'target_threshold': 'Minimum target count (e.g., 3)'
                },
                mitre_tactics=['Lateral Movement'],
                data_sources=['DeviceNetworkEvents']
            ),

            'anomaly_process_execution': QueryPattern(
                name='Process Execution Anomaly Detection',
                description='Detect anomalous process execution frequency using time-series analysis',
                category='threat_hunting',
                template='''// Process Execution Anomaly Detection
let lookback = {lookback};
let timeframe = {bin_size};
let sensitiveProcesses = dynamic({process_list});
let anomalyThreshold = {threshold};
DeviceProcessEvents
| where TimeGenerated >= ago(lookback)
| where FileName in~ (sensitiveProcesses)
| make-series ProcessCount = count() default=0
    on TimeGenerated
    from ago(lookback) to now()
    step timeframe
    by FileName, DeviceName
| extend (anomalies, score, baseline) = series_decompose_anomalies(ProcessCount, anomalyThreshold, -1, 'linefit')
| mv-expand TimeGenerated to typeof(datetime), ProcessCount to typeof(long), anomalies to typeof(int), score to typeof(double), baseline to typeof(double)
| where anomalies == 1
| project
    TimeGenerated,
    DeviceName,
    FileName,
    ProcessCount,
    Baseline = round(baseline, 2),
    AnomalyScore = round(score, 2)
| sort by AnomalyScore desc''',
                parameters={
                    'lookback': 'Historical baseline period (e.g., 30d)',
                    'bin_size': 'Time bucket size (e.g., 1h)',
                    'process_list': '["powershell.exe", "cmd.exe", "wmic.exe", "rundll32.exe"]',
                    'threshold': 'Anomaly sensitivity (e.g., 1.5 = moderate, 3.0 = conservative)'
                },
                mitre_tactics=['Execution', 'Discovery'],
                data_sources=['DeviceProcessEvents']
            ),

            'persistence_registry': QueryPattern(
                name='Persistence via Registry Run Keys',
                description='Detect persistence mechanisms using registry run keys',
                category='threat_hunting',
                template='''// Persistence Detection - Registry Run Keys
let timeframe = {timeframe};
let persistenceKeys = dynamic([
    @"Microsoft\\Windows\\CurrentVersion\\Run",
    @"Microsoft\\Windows\\CurrentVersion\\RunOnce",
    @"Microsoft\\Windows\\CurrentVersion\\RunOnceEx",
    @"Microsoft\\Windows NT\\CurrentVersion\\Winlogon"
]);
DeviceRegistryEvents
| where TimeGenerated > ago(timeframe)
| where ActionType == "RegistryValueSet"
| where RegistryKey has_any (persistenceKeys)
| extend
    KeyType = case(
        RegistryKey has "Run" and RegistryKey !has "Once", "Run",
        RegistryKey has "RunOnce", "RunOnce",
        RegistryKey has "Winlogon", "Winlogon",
        "Other"
    )
| project
    TimeGenerated,
    DeviceName,
    AccountName,
    InitiatingProcessFileName,
    InitiatingProcessCommandLine,
    RegistryKey,
    RegistryValueName,
    RegistryValueData,
    KeyType,
    PreviousRegistryValueData
| sort by TimeGenerated desc''',
                parameters={
                    'timeframe': 'Time window (e.g., 24h)'
                },
                mitre_tactics=['Persistence'],
                data_sources=['DeviceRegistryEvents']
            )
        }

    def _asim_patterns(self) -> Dict[str, QueryPattern]:
        """ASIM normalization patterns."""
        return {
            'asim_authentication': QueryPattern(
                name='ASIM Authentication Query',
                description='Source-agnostic authentication event query with filtering',
                category='asim',
                template='''// ASIM Authentication Events (Source-Agnostic)
_Im_Authentication(
    starttime=ago({timeframe}),
    endtime=now(),
    eventresult='{event_result}',
    username_has_any=dynamic({username_list})
)
| where EventType == '{event_type}'
| summarize
    EventCount = count(),
    UniqueUsers = dcount(TargetUsername),
    SourceIPs = make_set(SrcIpAddr),
    FirstEvent = min(TimeGenerated),
    LastEvent = max(TimeGenerated)
    by EventResult, LogonType, SrcIpAddr, TargetUsername
| project
    FirstEvent,
    LastEvent,
    EventResult,
    LogonType,
    TargetUsername,
    SrcIpAddr,
    EventCount,
    UniqueUsers,
    SourceIPs''',
                parameters={
                    'timeframe': 'Time window (e.g., 1h)',
                    'event_result': 'Success, Failure, or NA',
                    'event_type': 'Logon, Logoff, or Elevate',
                    'username_list': "['admin', 'root'] or []"
                },
                mitre_tactics=['Initial Access', 'Credential Access'],
                data_sources=['ASIM Authentication']
            ),

            'asim_network_session': QueryPattern(
                name='ASIM Network Session Query',
                description='Source-agnostic network session query with IP filtering',
                category='asim',
                template='''// ASIM Network Session Events (Source-Agnostic)
_Im_NetworkSession(
    starttime=ago({timeframe}),
    endtime=now(),
    srcipaddr_has_any_prefix=dynamic({src_ip_prefixes}),
    dstipaddr_has_any_prefix=dynamic({dst_ip_prefixes}),
    dstportnumber={dst_port}
)
| where NetworkDirection == '{direction}'
| summarize
    ConnectionCount = count(),
    BytesSent = sum(SrcBytes),
    BytesReceived = sum(DstBytes),
    UniqueDstIPs = dcount(DstIpAddr),
    UniqueSrcIPs = dcount(SrcIpAddr)
    by SrcIpAddr, DstIpAddr, DstPortNumber, NetworkProtocol
| extend TotalBytes = BytesSent + BytesReceived
| project
    SrcIpAddr,
    DstIpAddr,
    DstPortNumber,
    NetworkProtocol,
    ConnectionCount,
    BytesSent,
    BytesReceived,
    TotalBytes,
    UniqueDstIPs
| sort by TotalBytes desc''',
                parameters={
                    'timeframe': 'Time window (e.g., 1d)',
                    'src_ip_prefixes': '["10.0.", "192.168."] or []',
                    'dst_ip_prefixes': '[] for all',
                    'dst_port': 'Port number or 0 for all',
                    'direction': 'Inbound, Outbound, or NA'
                },
                mitre_tactics=['Command and Control', 'Exfiltration'],
                data_sources=['ASIM Network Session']
            ),

            'asim_dns': QueryPattern(
                name='ASIM DNS Query',
                description='Source-agnostic DNS query with response code filtering',
                category='asim',
                template='''// ASIM DNS Activity (Source-Agnostic)
_Im_Dns(
    starttime=ago({timeframe}),
    endtime=now(),
    responsecodename='{response_code}',
    domain_has_any=dynamic({domain_list})
)
| where QueryType == '{query_type}'
| summarize
    QueryCount = count(),
    UniqueClients = dcount(SrcIpAddr),
    ResponseCodes = make_set(ResponseCodeName)
    by DomainName, SrcIpAddr
| where QueryCount >= {threshold}
| project
    DomainName,
    SrcIpAddr,
    QueryCount,
    UniqueClients,
    ResponseCodes
| sort by QueryCount desc''',
                parameters={
                    'timeframe': 'Time window (e.g., 1h)',
                    'response_code': 'NXDOMAIN, NOERROR, SERVFAIL, or empty',
                    'domain_list': '[] for all or specific domains',
                    'query_type': 'A, AAAA, CNAME, MX, TXT, or empty',
                    'threshold': 'Minimum query count (e.g., 10)'
                },
                mitre_tactics=['Command and Control', 'Exfiltration'],
                data_sources=['ASIM DNS']
            )
        }

    def _optimization_patterns(self) -> Dict[str, QueryPattern]:
        """Performance optimization patterns."""
        return {
            'watchlist_join_optimized': QueryPattern(
                name='Optimized Watchlist Join',
                description='Efficient watchlist integration using SearchKey',
                category='optimization',
                template='''// Optimized Watchlist Join Pattern
let allowlist = _GetWatchlist('{watchlist_name}')
    | project SearchKey, {additional_fields};
{table_name}
| where TimeGenerated > ago({timeframe})
| where {initial_filters}
| join kind=leftanti (allowlist) on $left.{join_field} == $right.SearchKey
| project {output_fields}''',
                parameters={
                    'watchlist_name': 'Name of the watchlist',
                    'additional_fields': 'Extra fields from watchlist',
                    'table_name': 'Source table',
                    'timeframe': 'Time window',
                    'initial_filters': 'Filters before join',
                    'join_field': 'Field to join on',
                    'output_fields': 'Fields to return'
                },
                mitre_tactics=[],
                data_sources=['Watchlist']
            ),

            'high_cardinality_join': QueryPattern(
                name='High-Cardinality Join with Shuffle Hint',
                description='Optimized join for high-cardinality keys',
                category='optimization',
                template='''// High-Cardinality Join Optimization
let LeftTable = {left_table}
    | where TimeGenerated > ago({timeframe})
    | where {left_filters}
    | project {left_fields};
let RightTable = {right_table}
    | where TimeGenerated > ago({timeframe})
    | where {right_filters}
    | project {right_fields};
LeftTable
| join kind=inner hint.shufflekey={shuffle_key} (RightTable)
    on $left.{left_key} == $right.{right_key}
| project {output_fields}''',
                parameters={
                    'left_table': 'Smaller table',
                    'right_table': 'Larger table',
                    'timeframe': 'Time window',
                    'left_filters': 'Left table filters',
                    'right_filters': 'Right table filters',
                    'left_fields': 'Left table columns',
                    'right_fields': 'Right table columns',
                    'shuffle_key': 'High-cardinality join key (e.g., IPAddress)',
                    'left_key': 'Left join field',
                    'right_key': 'Right join field',
                    'output_fields': 'Result columns'
                },
                mitre_tactics=[],
                data_sources=[]
            ),

            'time_series_aggregation': QueryPattern(
                name='Optimized Time-Series Aggregation',
                description='Efficient time-series aggregation with binning',
                category='optimization',
                template='''// Time-Series Aggregation Pattern
{table_name}
| where TimeGenerated > ago({timeframe})
| where {filters}
| summarize
    {aggregations}
    by {group_by_fields}, bin(TimeGenerated, {bin_size})
| project {output_fields}
| render timechart''',
                parameters={
                    'table_name': 'Source table',
                    'timeframe': 'Time window (e.g., 7d)',
                    'filters': 'Initial filters',
                    'aggregations': 'count(), sum(), avg(), etc.',
                    'group_by_fields': 'Grouping dimensions',
                    'bin_size': 'Time bucket (e.g., 1h, 15m)',
                    'output_fields': 'Result columns'
                },
                mitre_tactics=[],
                data_sources=[]
            )
        }

    def get_pattern(self, pattern_name: str) -> Optional[QueryPattern]:
        """Retrieve a specific query pattern."""
        return self.patterns.get(pattern_name)

    def get_patterns_by_category(self, category: str) -> List[QueryPattern]:
        """Get all patterns in a category."""
        return [p for p in self.patterns.values() if p.category == category]

    def get_patterns_by_tactic(self, tactic: str) -> List[QueryPattern]:
        """Get patterns by MITRE ATT&CK tactic."""
        return [
            p for p in self.patterns.values()
            if p.mitre_tactics and tactic in p.mitre_tactics
        ]

    def list_all_patterns(self) -> List[str]:
        """List all available pattern names."""
        return list(self.patterns.keys())

    def format_pattern(self, pattern_name: str, **kwargs) -> str:
        """
        Format a pattern template with provided parameters.

        Args:
            pattern_name: Name of the pattern
            **kwargs: Parameter values to substitute

        Returns:
            Formatted KQL query string
        """
        pattern = self.get_pattern(pattern_name)
        if not pattern:
            raise ValueError(f"Pattern '{pattern_name}' not found")

        # Replace parameters in template
        query = pattern.template
        for param, value in kwargs.items():
            placeholder = f"{{{param}}}"
            query = query.replace(placeholder, str(value))

        return query


# Example usage
if __name__ == "__main__":
    patterns = KQLPatterns()

    # List all patterns
    print("Available patterns:")
    for name in patterns.list_all_patterns():
        pattern = patterns.get_pattern(name)
        if pattern:
            print(f"  - {name}: {pattern.description}")

    # Format a pattern
    brute_force_query = patterns.format_pattern(
        'brute_force_auth',
        threshold=10,
        timeframe='1h'
    )
    print(f"\nBrute Force Query:\n{brute_force_query}")
