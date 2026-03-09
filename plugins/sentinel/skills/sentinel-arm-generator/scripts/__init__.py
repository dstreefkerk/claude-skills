"""
Microsoft Sentinel ARM Template Generator Skill

Generates deployment-ready Sentinel Analytic Rule ARM templates from KQL queries
with intelligent auto-generation of metadata, MITRE mappings, and entity extraction.
"""

from .generate_arm_template import SentinelARMGenerator, generate_sentinel_arm_template
from .kql_analyzer import KQLAnalyzer
from .mitre_attack_mapper import MitreAttackMapper
from .entity_extractor import EntityExtractor

__all__ = [
    "SentinelARMGenerator",
    "generate_sentinel_arm_template",
    "KQLAnalyzer",
    "MitreAttackMapper",
    "EntityExtractor",
]
