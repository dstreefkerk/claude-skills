"""
Entity Extraction Module

Analyzes KQL queries to automatically identify and map Sentinel entity types
(Account, IP, Host, Process, File, URL, etc.) based on column names and patterns.
"""

from typing import Dict, List, Any, Optional
import re


class EntityExtractor:
    """Extract and map Sentinel entity types from KQL queries."""

    # Entity type mapping rules
    ENTITY_PATTERNS = {
        "Account": {
            "column_patterns": [
                r"UserPrincipalName",
                r"AccountName",
                r"TargetUserName",
                r"InitiatingProcessAccountName",
                r"AccountUpn",
                r"UserName",
                r"User",
                r"TargetAccount",
                r"SourceUserName"
            ],
            "identifiers": {
                "FullName": ["UserPrincipalName", "AccountName", "TargetUserName", "User"],
                "Name": ["AccountName", "UserName", "TargetAccount"],
                "UPNSuffix": ["UserPrincipalName"],
                "AadUserId": ["AadUserId", "UserId"],
                "Sid": ["AccountSid", "UserSid", "TargetSid"]
            }
        },
        "IP": {
            "column_patterns": [
                r"IPAddress",
                r"SourceIP",
                r"DestinationIP",
                r"ClientIP",
                r"RemoteIP",
                r"RemoteIPAddress",
                r"LocalIP",
                r"IpAddress"
            ],
            "identifiers": {
                "Address": ["IPAddress", "SourceIP", "DestinationIP", "ClientIP", "RemoteIP", "RemoteIPAddress", "LocalIP", "IpAddress"]
            }
        },
        "Host": {
            "column_patterns": [
                r"DeviceName",
                r"ComputerName",
                r"Computer",
                r"HostName",
                r"MachineName",
                r"Device",
                r"WorkstationName"
            ],
            "identifiers": {
                "HostName": ["DeviceName", "ComputerName", "Computer", "HostName", "MachineName", "WorkstationName"],
                "DnsDomain": ["DnsDomain"],
                "NetBiosName": ["NetBiosName"],
                "AzureID": ["AzureDeviceId", "DeviceId"]
            }
        },
        "Process": {
            "column_patterns": [
                r"ProcessName",
                r"InitiatingProcessFileName",
                r"ProcessCommandLine",
                r"CommandLine",
                r"InitiatingProcessCommandLine",
                r"FileName",
                r"Image"
            ],
            "identifiers": {
                "ProcessId": ["ProcessId", "InitiatingProcessId", "PID"],
                "CommandLine": ["ProcessCommandLine", "CommandLine", "InitiatingProcessCommandLine"],
                "ElevationToken": ["TokenElevationType"]
            }
        },
        "File": {
            "column_patterns": [
                r"FileName",
                r"FilePath",
                r"FolderPath",
                r"TargetFilename",
                r"InitiatingProcessFileName"
            ],
            "identifiers": {
                "Name": ["FileName", "TargetFilename"],
                "Directory": ["FolderPath", "FilePath"],
                "FileHash": ["SHA256", "SHA1", "MD5", "FileHash"]
            }
        },
        "URL": {
            "column_patterns": [
                r"Url",
                r"FileOriginUrl",
                r"RemoteUrl",
                r"RequestURL",
                r"UrlOriginal"
            ],
            "identifiers": {
                "Url": ["Url", "FileOriginUrl", "RemoteUrl", "RequestURL", "UrlOriginal"]
            }
        },
        "RegistryKey": {
            "column_patterns": [
                r"RegistryKey",
                r"TargetObject",
                r"RegistryPath"
            ],
            "identifiers": {
                "Hive": ["RegistryKey"],
                "Key": ["RegistryKey", "TargetObject", "RegistryPath"]
            }
        },
        "RegistryValue": {
            "column_patterns": [
                r"RegistryValueName",
                r"RegistryValueData",
                r"Details"
            ],
            "identifiers": {
                "Name": ["RegistryValueName"],
                "Value": ["RegistryValueData", "Details"],
                "ValueType": ["RegistryValueType"]
            }
        },
        "DNS": {
            "column_patterns": [
                r"DomainName",
                r"QueryName",
                r"DnsQuery",
                r"Domain"
            ],
            "identifiers": {
                "DomainName": ["DomainName", "QueryName", "DnsQuery", "Domain"]
            }
        },
        "FileHash": {
            "column_patterns": [
                r"SHA256",
                r"SHA1",
                r"MD5",
                r"FileHash"
            ],
            "identifiers": {
                "Algorithm": [],  # Inferred from column name
                "Value": ["SHA256", "SHA1", "MD5", "FileHash"]
            }
        },
        "CloudApplication": {
            "column_patterns": [
                r"AppDisplayName",
                r"ApplicationId",
                r"ServicePrincipalName"
            ],
            "identifiers": {
                "Name": ["AppDisplayName"],
                "AppId": ["ApplicationId"]
            }
        },
        "Mailbox": {
            "column_patterns": [
                r"MailboxPrimaryAddress",
                r"RecipientEmailAddress",
                r"SenderAddress"
            ],
            "identifiers": {
                "MailboxPrimaryAddress": ["MailboxPrimaryAddress", "RecipientEmailAddress"],
                "DisplayName": ["RecipientDisplayName"]
            }
        }
    }

    def __init__(self, kql_query: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize entity extractor.

        Args:
            kql_query: KQL detection query
            context: Optional user context
        """
        self.kql_query = kql_query
        self.context = context or {}
        self.detected_columns = self._extract_column_names()

    def _extract_column_names(self) -> List[str]:
        """
        Extract column names from KQL query (project, extend, summarize).

        Returns:
            List of column names found in query
        """
        columns = []

        # Match project statements
        project_matches = re.findall(r'\bproject\s+([^|]+)', self.kql_query, re.IGNORECASE)
        for match in project_matches:
            cols = [col.strip().split('=')[0].strip() for col in match.split(',')]
            columns.extend(cols)

        # Match extend statements
        extend_matches = re.findall(r'\bextend\s+([^|]+)', self.kql_query, re.IGNORECASE)
        for match in extend_matches:
            cols = [col.strip().split('=')[0].strip() for col in match.split(',')]
            columns.extend(cols)

        # Match summarize output columns
        summarize_matches = re.findall(r'\bsummarize\s+([^|]+?\bby\b)', self.kql_query, re.IGNORECASE)
        for match in summarize_matches:
            cols = [col.strip().split('=')[0].strip() for col in match.replace('by', '').split(',')]
            columns.extend(cols)

        # Match summarize by columns
        by_matches = re.findall(r'\bby\s+([^|]+)', self.kql_query, re.IGNORECASE)
        for match in by_matches:
            cols = [col.strip().split(',')[0].strip() for col in match.split(',')]
            columns.extend(cols)

        # Also look for common columns in where clauses (might be available for mapping)
        where_matches = re.findall(r'\bwhere\s+(\w+)', self.kql_query, re.IGNORECASE)
        columns.extend(where_matches)

        # Remove duplicates and clean
        columns = list(set([col for col in columns if col and not col.startswith('(')]))

        return columns

    def extract_entities(self) -> List[Dict[str, Any]]:
        """
        Extract entity mappings from KQL query.

        Returns:
            List of entity mapping dictionaries
        """
        # Check for user-specified entity mappings
        if self.context.get("entity_mappings"):
            return self.context["entity_mappings"]

        entity_mappings = []
        detected_entity_types = set()

        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            # Find matching columns for this entity type
            matched_columns = []

            for column in self.detected_columns:
                for pattern in patterns["column_patterns"]:
                    if re.search(pattern, column, re.IGNORECASE):
                        matched_columns.append(column)
                        break

            if matched_columns:
                # Build field mappings
                field_mappings = []

                for identifier, identifier_columns in patterns["identifiers"].items():
                    for col in matched_columns:
                        # Check if column matches this identifier
                        for id_col_pattern in identifier_columns:
                            if re.search(id_col_pattern, col, re.IGNORECASE):
                                # Special handling for FileHash
                                if entity_type == "FileHash":
                                    algorithm = self._detect_hash_algorithm(col)
                                    field_mappings.append({
                                        "identifier": "Algorithm",
                                        "columnName": algorithm
                                    })
                                    field_mappings.append({
                                        "identifier": "Value",
                                        "columnName": col
                                    })
                                else:
                                    field_mappings.append({
                                        "identifier": identifier,
                                        "columnName": col
                                    })
                                break

                # Remove duplicate field mappings
                seen = set()
                unique_mappings = []
                for fm in field_mappings:
                    key = (fm["identifier"], fm["columnName"])
                    if key not in seen:
                        seen.add(key)
                        unique_mappings.append(fm)

                if unique_mappings and entity_type not in detected_entity_types:
                    entity_mappings.append({
                        "entityType": entity_type,
                        "fieldMappings": unique_mappings
                    })
                    detected_entity_types.add(entity_type)

        return entity_mappings

    def _detect_hash_algorithm(self, column_name: str) -> str:
        """
        Detect hash algorithm from column name.

        Args:
            column_name: Column name

        Returns:
            Algorithm name (SHA256, SHA1, MD5)
        """
        column_lower = column_name.lower()

        if "sha256" in column_lower:
            return "SHA256"
        elif "sha1" in column_lower:
            return "SHA1"
        elif "md5" in column_lower:
            return "MD5"
        else:
            return "Unknown"

    def get_entity_summary(self) -> Dict[str, List[str]]:
        """
        Get summary of detected entities and their columns.

        Returns:
            Dictionary mapping entity types to column lists
        """
        entity_mappings = self.extract_entities()

        summary = {}
        for mapping in entity_mappings:
            entity_type = mapping["entityType"]
            columns = [fm["columnName"] for fm in mapping["fieldMappings"]]
            summary[entity_type] = list(set(columns))

        return summary

    def validate_entity_mappings(self, entity_mappings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate entity mappings for correctness.

        Args:
            entity_mappings: Entity mappings to validate

        Returns:
            Validation result with warnings/errors
        """
        validation = {
            "valid": True,
            "warnings": [],
            "errors": []
        }

        valid_entity_types = list(self.ENTITY_PATTERNS.keys())

        for mapping in entity_mappings:
            entity_type = mapping.get("entityType")
            field_mappings = mapping.get("fieldMappings", [])

            # Check entity type is valid
            if entity_type not in valid_entity_types:
                validation["errors"].append(f"Invalid entity type: {entity_type}")
                validation["valid"] = False

            # Check field mappings exist
            if not field_mappings:
                validation["warnings"].append(f"No field mappings for entity type: {entity_type}")

            # Check identifiers are valid for this entity type
            if entity_type in self.ENTITY_PATTERNS:
                valid_identifiers = list(self.ENTITY_PATTERNS[entity_type]["identifiers"].keys())
                for fm in field_mappings:
                    identifier = fm.get("identifier")
                    if identifier not in valid_identifiers:
                        validation["warnings"].append(
                            f"Unusual identifier '{identifier}' for entity type '{entity_type}'. "
                            f"Expected one of: {', '.join(valid_identifiers)}"
                        )

        return validation
