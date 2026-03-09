# ARM Template Reference

ARM template structure and schema standards for Microsoft Sentinel analytic rules.

---

## ARM Template Structure

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "workspace": { "type": "String" }
  },
  "resources": [{
    "id": "[concat(resourceId('Microsoft.OperationalInsights/workspaces/providers', parameters('workspace'), 'Microsoft.SecurityInsights'),'/alertRules/{GUID}')]",
    "name": "[concat(parameters('workspace'),'/Microsoft.SecurityInsights/{GUID}')]",
    "type": "Microsoft.OperationalInsights/workspaces/providers/alertRules",
    "kind": "Scheduled",
    "apiVersion": "2023-12-01-preview",
    "properties": {
      "displayName": "Rule Name",
      "description": "Rule description",
      "severity": "Medium",
      "enabled": false,
      "query": "KQL query here",
      "queryFrequency": "PT5M",
      "queryPeriod": "PT10M",
      "triggerOperator": "GreaterThan",
      "triggerThreshold": 0,
      "suppressionDuration": "PT1H",
      "suppressionEnabled": false,
      "tactics": ["InitialAccess"],
      "techniques": ["T1078"],
      "subTechniques": ["T1078.004"],
      "incidentConfiguration": {
        "createIncident": true,
        "groupingConfiguration": {
          "enabled": false,
          "reopenClosedIncident": false,
          "lookbackDuration": "PT5H",
          "matchingMethod": "AllEntities",
          "groupByEntities": [],
          "groupByAlertDetails": [],
          "groupByCustomDetails": []
        }
      },
      "eventGroupingSettings": {
        "aggregationKind": "SingleAlert"
      },
      "entityMappings": []
    }
  }]
}
```

---

## API Version

Current: **2023-12-01-preview**

---

## Required vs Optional Properties

### Required Properties
- displayName, description, severity, enabled
- query, queryFrequency, queryPeriod
- triggerOperator, triggerThreshold
- incidentConfiguration, eventGroupingSettings

### Optional Properties
- tactics, techniques, subTechniques (when patterns match)
- entityMappings (when entities detected, max 5)
- customDetails (for additional SOC context)
- alertDetailsOverride (for dynamic alert enrichment)

### Never Include (for custom rules)
- `templateVersion` - Only valid when `alertRuleTemplateName` is specified
- `alertRuleTemplateName` - Only for rules based on Microsoft templates

---

## Custom Details

Surface KQL columns directly into incidents (no parameter limit):

```json
"customDetails": {
  "RiskLevel": "RiskLevel_Column",
  "ProcessName": "ProcessName_Column",
  "TargetResource": "TargetResource_Column"
}
```

---

## Alert Details Override

Dynamic alert enrichment from KQL columns:

```json
"alertDetailsOverride": {
  "alertDisplayNameFormat": "{{Operation}} on {{TargetHost}}",
  "alertDescriptionFormat": "User {{InitiatedBy}} performed {{Operation}}",
  "alertSeverityColumnName": "DynamicSeverity",
  "alertTacticsColumnName": "DynamicTactic",
  "alertDynamicProperties": []
}
```

**Limits:**
- alertDisplayNameFormat: Max 2-3 parameters recommended
- alertDescriptionFormat: **Maximum 3 parameters enforced**
- Use customDetails for additional context

---

## Event Grouping Settings

| Aggregation | Use When |
|-------------|----------|
| SingleAlert | Threshold-based, correlation rules, uses `summarize count()` |
| AlertPerResult | Each row is distinct incident, high-fidelity detections |

---

## KQL JSON Escaping

| KQL Character | JSON Escape |
|---------------|-------------|
| `"` (quote) | `\"` |
| `\` (backslash) | `\\` |
| Newline | `\n` |
| Tab | `\t` |

Example:
```
// KQL:    | where Path contains "C:\Windows\Temp"
// JSON:   "| where Path contains \"C:\\Windows\\Temp\""
```

---

## Query Frequency/Period Recommendations

**Critical**: Always set `queryPeriod` > `queryFrequency` for ingestion lag buffer.

| Detection Type | queryFrequency | queryPeriod | Buffer |
|---------------|----------------|-------------|--------|
| Real-Time Critical | PT5M | PT10M | +5 min |
| Real-Time Standard | PT5M | PT15M | +10 min |
| Hourly | PT1H | PT2H | +1 hour |
| Daily | P1D | P1D | Use TimeGenerated filter |

---

## NRT Rules (Near Real-Time)

Different schema - no frequency/period/trigger properties:

```json
{
  "kind": "NRT",
  "properties": {
    "query": "Your KQL query"
    // NO queryFrequency, queryPeriod, triggerOperator, triggerThreshold
  }
}
```

**Limitations:** 30-second query timeout, limited data sources.

---

## Deployment Parameterization

For multi-environment deployment:

```json
"parameters": {
  "workspace": { "type": "String" },
  "ruleEnabled": {
    "type": "bool",
    "defaultValue": false
  },
  "ruleSeverity": {
    "type": "string",
    "defaultValue": "Medium",
    "allowedValues": ["High", "Medium", "Low", "Informational"]
  }
}
```

Reference: `"enabled": "[parameters('ruleEnabled')]"`

---

## Deployment Commands

**Azure CLI:**
```bash
az deployment group create \
  --resource-group <rg-name> \
  --template-file sentinel-rule.json \
  --parameters workspace=<workspace-name>
```

**PowerShell:**
```powershell
New-AzResourceGroupDeployment `
  -ResourceGroupName <rg-name> `
  -TemplateFile sentinel-rule.json `
  -workspace <workspace-name>
```
