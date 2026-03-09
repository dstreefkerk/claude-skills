"""
Microsoft Sentinel ARM Template Generator - Main Module

Generates deployment-ready Sentinel Analytic Rule ARM templates from KQL queries
with intelligent auto-generation of metadata, MITRE mappings, and entity extraction.
"""

import json
import uuid
from typing import Dict, List, Any, Optional


class SentinelARMGenerator:
    """Main class for generating Sentinel Analytic Rule ARM templates."""

    def __init__(self, kql_query: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize ARM template generator.

        Args:
            kql_query: The KQL detection query
            context: Optional context dict with user overrides and conversation context
        """
        self.kql_query = kql_query.strip()
        self.context = context or {}
        self.rule_guid = str(uuid.uuid4())

    def generate_template(self) -> Dict[str, Any]:
        """
        Generate complete ARM template for Sentinel Analytic Rule.

        Returns:
            Complete ARM template as dictionary
        """
        # Import sub-modules for processing
        from .mitre_attack_mapper import MitreAttackMapper
        from .entity_extractor import EntityExtractor
        from .kql_analyzer import KQLAnalyzer

        # Analyze KQL query
        analyzer = KQLAnalyzer(self.kql_query, self.context)
        analysis = analyzer.analyze()

        # Get MITRE mappings
        mitre_mapper = MitreAttackMapper(self.kql_query, self.context, analysis)
        mitre_mappings = mitre_mapper.get_mappings()

        # Extract entities
        entity_extractor = EntityExtractor(self.kql_query, self.context)
        entity_mappings = entity_extractor.extract_entities()

        # Build ARM template
        template = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {
                "workspace": {
                    "type": "String"
                }
            },
            "resources": [
                {
                    "id": f"[concat(resourceId('Microsoft.OperationalInsights/workspaces/providers', parameters('workspace'), 'Microsoft.SecurityInsights'),'/alertRules/{self.rule_guid}')]",
                    "name": f"[concat(parameters('workspace'),'/Microsoft.SecurityInsights/{self.rule_guid}')]",
                    "type": "Microsoft.OperationalInsights/workspaces/providers/alertRules",
                    "kind": "Scheduled",
                    "apiVersion": "2023-12-01-preview",
                    "properties": self._build_properties(
                        analysis, mitre_mappings, entity_mappings
                    )
                }
            ]
        }

        return template

    def _build_properties(
        self,
        analysis: Dict[str, Any],
        mitre_mappings: Dict[str, List[str]],
        entity_mappings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build the properties section of the ARM template.

        Args:
            analysis: KQL analysis results
            mitre_mappings: MITRE ATT&CK mappings
            entity_mappings: Entity field mappings

        Returns:
            Properties dictionary
        """
        properties = {
            "displayName": self.context.get("display_name") or analysis["display_name"],
            "description": self.context.get("description") or analysis["description"],
            "severity": self.context.get("severity") or analysis["severity"],
            "enabled": self.context.get("enabled", False),
            "query": self.kql_query,
            "queryFrequency": self.context.get("query_frequency") or analysis["query_frequency"],
            "queryPeriod": self.context.get("query_period") or analysis["query_period"],
            "triggerOperator": self.context.get("trigger_operator") or analysis["trigger_operator"],
            "triggerThreshold": self.context.get("trigger_threshold", analysis["trigger_threshold"]),
            "suppressionDuration": self.context.get("suppression_duration", "PT1H"),
            "suppressionEnabled": self.context.get("suppression_enabled", False),
            "incidentConfiguration": {
                "createIncident": True,
                "groupingConfiguration": {
                    "enabled": False,
                    "reopenClosedIncident": False,
                    "lookbackDuration": "PT5H",
                    "matchingMethod": "AllEntities",
                    "groupByEntities": [],
                    "groupByAlertDetails": [],
                    "groupByCustomDetails": []
                }
            },
            "eventGroupingSettings": {
                "aggregationKind": "SingleAlert"
            }
            # NOTE: templateVersion is NOT included for custom rules
            # It can only be used when alertRuleTemplateName is specified
        }

        # Add MITRE tactics/techniques if detected
        if mitre_mappings.get("tactics"):
            properties["tactics"] = mitre_mappings["tactics"]
        if mitre_mappings.get("techniques"):
            properties["techniques"] = mitre_mappings["techniques"]
        if mitre_mappings.get("sub_techniques"):
            properties["subTechniques"] = mitre_mappings["sub_techniques"]

        # Add entity mappings if detected
        if entity_mappings:
            properties["entityMappings"] = entity_mappings

        return properties

    def save_template(self, output_path: str) -> None:
        """
        Generate and save ARM template to file.

        Args:
            output_path: Path to save JSON file
        """
        template = self.generate_template()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=4, ensure_ascii=False)

    def get_deployment_instructions(self, rule_name: str, workspace_name: str = "<sentinel-workspace-name>") -> str:
        """
        Generate deployment instructions for the ARM template.

        Args:
            rule_name: Name of the rule (for file naming)
            workspace_name: Sentinel workspace name (default placeholder)

        Returns:
            Formatted deployment instructions
        """
        file_name = f"sentinel-rule-{rule_name}.json"

        instructions = f"""
# Deployment Instructions for {rule_name}

## File Generated
- **Template**: {file_name}
- **Rule GUID**: {self.rule_guid}
- **API Version**: 2023-12-01-preview

## Azure CLI Deployment

```bash
az deployment group create \\
  --resource-group <resource-group-name> \\
  --template-file {file_name} \\
  --parameters workspace={workspace_name}
```

## Azure PowerShell Deployment

```powershell
New-AzResourceGroupDeployment `
  -ResourceGroupName <resource-group-name> `
  -TemplateFile {file_name} `
  -workspace {workspace_name}
```

## Azure Portal Deployment

1. Navigate to Azure Portal > Deploy a custom template
2. Click "Build your own template in the editor"
3. Upload {file_name}
4. Provide workspace parameter: {workspace_name}
5. Review and create deployment

## Validation

After deployment, verify the rule in Sentinel:
1. Navigate to Microsoft Sentinel > Analytics
2. Search for rule by display name
3. Verify enabled status and configuration
4. Test rule execution and alert generation

## Next Steps

1. **Enable Rule**: Set "enabled": true in template or enable via portal
2. **Tune Threshold**: Adjust triggerThreshold based on alert volume
3. **Configure Playbooks**: Attach automated response playbooks if needed
4. **Set Notifications**: Configure alert notification emails
5. **Monitor Performance**: Check query execution time and resource usage
"""
        return instructions

    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Generate validation summary showing all auto-generated fields.

        Returns:
            Dictionary with validation details
        """
        from .mitre_attack_mapper import MitreAttackMapper
        from .entity_extractor import EntityExtractor
        from .kql_analyzer import KQLAnalyzer

        analyzer = KQLAnalyzer(self.kql_query, self.context)
        analysis = analyzer.analyze()

        mitre_mapper = MitreAttackMapper(self.kql_query, self.context, analysis)
        mitre_mappings = mitre_mapper.get_mappings()

        entity_extractor = EntityExtractor(self.kql_query, self.context)
        entity_mappings = entity_extractor.extract_entities()

        summary = {
            "rule_guid": self.rule_guid,
            "display_name": analysis["display_name"],
            "description": analysis["description"],
            "severity": analysis["severity"],
            "severity_rationale": analysis["severity_rationale"],
            "query_frequency": analysis["query_frequency"],
            "query_period": analysis["query_period"],
            "frequency_rationale": analysis["frequency_rationale"],
            "trigger_operator": analysis["trigger_operator"],
            "trigger_threshold": analysis["trigger_threshold"],
            "mitre_tactics": mitre_mappings.get("tactics", []),
            "mitre_techniques": mitre_mappings.get("techniques", []),
            "mitre_sub_techniques": mitre_mappings.get("sub_techniques", []),
            "mitre_rationale": mitre_mappings.get("rationale", ""),
            "detected_entities": [
                {
                    "entity_type": em["entityType"],
                    "mapped_columns": [fm["columnName"] for fm in em["fieldMappings"]]
                }
                for em in entity_mappings
            ],
            "data_sources": analysis.get("data_sources", []),
            "user_overrides": {
                k: v for k, v in self.context.items()
                if k in ["display_name", "description", "severity", "query_frequency",
                        "query_period", "trigger_threshold"]
            }
        }

        return summary


def generate_sentinel_arm_template(
    kql_query: str,
    context: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
    validation_only: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to generate Sentinel ARM template.

    Args:
        kql_query: KQL detection query
        context: Optional context with overrides
        output_path: Optional path to save JSON file
        validation_only: If True, only return validation summary

    Returns:
        Dictionary with template and/or validation summary
    """
    generator = SentinelARMGenerator(kql_query, context)

    if validation_only:
        return {
            "validation_summary": generator.get_validation_summary(),
            "deployment_instructions": None,
            "template": None
        }

    template = generator.generate_template()

    result = {
        "template": template,
        "validation_summary": generator.get_validation_summary(),
        "deployment_instructions": None
    }

    if output_path:
        generator.save_template(output_path)
        # Extract rule name from display name for instructions
        rule_name = generator.get_validation_summary()["display_name"].lower()
        rule_name = rule_name.replace(" ", "-").replace("_", "-")
        result["deployment_instructions"] = generator.get_deployment_instructions(rule_name)

    return result
