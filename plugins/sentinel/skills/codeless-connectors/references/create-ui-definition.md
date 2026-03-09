# createUiDefinition.json Builder Guide

Guide for building `createUiDefinition.json` files that provide the Azure Portal deployment UI for ARM templates. Used alongside Sentinel connector ARM templates for marketplace deployment.

Source: https://learn.microsoft.com/azure/azure-resource-manager/managed-applications/create-uidefinition-overview

---

## Basic Structure

```json
{
    "$schema": "https://schema.management.azure.com/schemas/0.1.2-preview/CreateUIDefinition.MultiVm.json#",
    "handler": "Microsoft.Azure.CreateUIDef",
    "version": "0.1.2-preview",
    "parameters": {
        "config": {
            "isWizard": false,
            "basics": {}
        },
        "basics": [],
        "steps": [],
        "outputs": {}
    }
}
```

| Property | Required | Description |
|----------|----------|-------------|
| `$schema` | Recommended | Schema URI — version must match `version` field |
| `handler` | Yes | Always `Microsoft.Azure.CreateUIDef` |
| `version` | Yes | `0.1.2-preview` |
| `parameters.config` | No | Override default behavior of basics step |
| `parameters.basics` | Yes | Elements displayed on the Basics step |
| `parameters.steps` | Yes | Array of additional steps (tabs) after Basics |
| `parameters.outputs` | Yes | Maps UI element values to ARM template parameters |

---

## Steps Configuration

Steps appear as tabs in the Azure Portal deployment UI. Each step contains an array of elements.

```json
"steps": [
    {
        "name": "connectionConfig",
        "label": "Connection Configuration",
        "elements": [
            { /* element definitions */ }
        ]
    },
    {
        "name": "credentials",
        "label": "Credentials",
        "elements": [
            { /* element definitions */ }
        ]
    }
]
```

| Property | Required | Description |
|----------|----------|-------------|
| `name` | Yes | Internal identifier, used to reference step in outputs |
| `label` | Yes | Display text shown on the tab |
| `elements` | Yes | Array of UI elements |

---

## Common Element Types

### Microsoft.Common.TextBox

Standard text input field.

```json
{
    "name": "apiEndpoint",
    "type": "Microsoft.Common.TextBox",
    "label": "API Endpoint URL",
    "toolTip": "Enter the base URL of the API to poll.",
    "defaultValue": "https://api.example.com/v1/events",
    "constraints": {
        "required": true,
        "regex": "^https?://[^\\s]+$",
        "validationMessage": "Must be a valid URL starting with http:// or https://"
    },
    "visible": true
}
```

| Property | Description |
|----------|-------------|
| `constraints.required` | Whether the field is required |
| `constraints.regex` | Regex pattern for validation |
| `constraints.validationMessage` | Message shown when validation fails |

### Microsoft.Common.PasswordBox

Secure password input (masked).

```json
{
    "name": "apiSecret",
    "type": "Microsoft.Common.PasswordBox",
    "label": {
        "password": "API Secret",
        "confirmPassword": "Confirm API Secret"
    },
    "toolTip": "Enter the API secret key.",
    "constraints": {
        "required": true,
        "regex": "^.{8,}$",
        "validationMessage": "Must be at least 8 characters."
    },
    "options": {
        "hideConfirmation": true
    },
    "visible": true
}
```

| Property | Description |
|----------|-------------|
| `label.password` | Label for password field |
| `label.confirmPassword` | Label for confirmation field |
| `options.hideConfirmation` | Set `true` to hide the confirmation input |

### Microsoft.Common.DropDown

Selection dropdown.

```json
{
    "name": "pollingInterval",
    "type": "Microsoft.Common.DropDown",
    "label": "Polling Interval (minutes)",
    "defaultValue": "5",
    "toolTip": "How often the connector polls the API.",
    "constraints": {
        "required": true,
        "allowedValues": [
            { "label": "1 minute", "value": "1" },
            { "label": "5 minutes", "value": "5" },
            { "label": "10 minutes", "value": "10" },
            { "label": "15 minutes", "value": "15" }
        ]
    },
    "visible": true
}
```

### Microsoft.Common.TextBlock

Read-only informational text block.

```json
{
    "name": "infoText",
    "type": "Microsoft.Common.TextBlock",
    "visible": true,
    "options": {
        "text": "This connector polls the vendor API for security events and ingests them into Microsoft Sentinel.",
        "link": {
            "label": "Learn more",
            "uri": "https://docs.example.com"
        }
    }
}
```

### Microsoft.Common.InfoBox

Information, warning, or error message box.

```json
{
    "name": "warningBox",
    "type": "Microsoft.Common.InfoBox",
    "visible": true,
    "options": {
        "icon": "Warning",
        "text": "You must have API admin access to generate the required credentials."
    }
}
```

| `icon` value | Description |
|-------------|-------------|
| `None` | No icon |
| `Info` | Blue info icon |
| `Warning` | Yellow warning icon |
| `Error` | Red error icon |

### Microsoft.Common.Section

Groups related elements visually.

```json
{
    "name": "authSection",
    "type": "Microsoft.Common.Section",
    "label": "Authentication Settings",
    "elements": [
        { /* nested elements */ }
    ],
    "visible": true
}
```

### Microsoft.Common.CheckBox

Boolean checkbox.

```json
{
    "name": "enableAdvanced",
    "type": "Microsoft.Common.CheckBox",
    "label": "Enable advanced filtering",
    "toolTip": "Filter events before ingestion.",
    "constraints": {
        "required": false
    }
}
```

### Microsoft.Common.OptionsGroup

Radio button group.

```json
{
    "name": "authType",
    "type": "Microsoft.Common.OptionsGroup",
    "label": "Authentication Type",
    "defaultValue": "API Key",
    "toolTip": "Select the authentication method.",
    "constraints": {
        "required": true,
        "allowedValues": [
            { "label": "API Key", "value": "apikey" },
            { "label": "OAuth2", "value": "oauth2" },
            { "label": "Basic Auth", "value": "basic" }
        ]
    },
    "visible": true
}
```

---

## Outputs

The `outputs` section maps UI element values to ARM template parameters. Keys must match ARM template parameter names.

```json
"outputs": {
    "workspace": "[basics('workspace')]",
    "apiEndpoint": "[steps('connectionConfig').apiEndpoint]",
    "apiSecret": "[steps('credentials').apiSecret]",
    "pollingInterval": "[steps('connectionConfig').pollingInterval]"
}
```

### Output Reference Syntax

| Expression | Description |
|-----------|-------------|
| `[basics('elementName')]` | Reference element in Basics step |
| `[steps('stepName').elementName]` | Reference element in a named step |
| `[steps('stepName').sectionName.elementName]` | Reference element inside a Section |

---

## Common Patterns for Sentinel Connectors

### Workspace Selector (Basics Step)

For Sentinel connector ARM templates, the workspace is typically selected in the Basics step via the `config` property:

```json
"config": {
    "isWizard": false,
    "basics": {
        "description": "**Vendor Connector** for Microsoft Sentinel.\n\nThis connector polls the Vendor API and ingests events.",
        "subscription": {
            "resourceProviders": [
                "Microsoft.OperationalInsights"
            ]
        },
        "location": {
            "label": "Location",
            "toolTip": "Select the location for the workspace.",
            "resourceTypes": [
                "Microsoft.OperationalInsights/workspaces"
            ]
        }
    }
}
```

The basics step automatically provides subscription and resource group selectors.

### Workspace Parameter in Basics

```json
"basics": [
    {
        "name": "workspace",
        "type": "Microsoft.Solutions.ResourceSelector",
        "label": "Log Analytics Workspace",
        "resourceType": "Microsoft.OperationalInsights/workspaces",
        "toolTip": "Select the Sentinel workspace.",
        "constraints": {
            "required": true
        }
    }
]
```

### API Key Authentication

```json
{
    "name": "credentials",
    "label": "Credentials",
    "elements": [
        {
            "name": "infoBox",
            "type": "Microsoft.Common.TextBlock",
            "options": {
                "text": "Enter your API credentials. You can find these in the vendor's admin console under Settings > API Keys."
            }
        },
        {
            "name": "apiKeyId",
            "type": "Microsoft.Common.TextBox",
            "label": "API Key ID",
            "toolTip": "The API key identifier.",
            "constraints": {
                "required": true,
                "regex": "^[a-zA-Z0-9-]+$",
                "validationMessage": "API Key ID must contain only alphanumeric characters and hyphens."
            }
        },
        {
            "name": "apiKeySecret",
            "type": "Microsoft.Common.PasswordBox",
            "label": {
                "password": "API Key Secret",
                "confirmPassword": "Confirm API Key Secret"
            },
            "toolTip": "The API key secret.",
            "constraints": {
                "required": true
            },
            "options": {
                "hideConfirmation": true
            }
        }
    ]
}
```

### OAuth2 Client Credentials

```json
{
    "name": "credentials",
    "label": "OAuth2 Credentials",
    "elements": [
        {
            "name": "clientId",
            "type": "Microsoft.Common.TextBox",
            "label": "Client ID",
            "toolTip": "OAuth2 application client ID.",
            "constraints": {
                "required": true
            }
        },
        {
            "name": "clientSecret",
            "type": "Microsoft.Common.PasswordBox",
            "label": {
                "password": "Client Secret",
                "confirmPassword": "Confirm Client Secret"
            },
            "toolTip": "OAuth2 application client secret.",
            "constraints": {
                "required": true
            },
            "options": {
                "hideConfirmation": true
            }
        },
        {
            "name": "tenantId",
            "type": "Microsoft.Common.TextBox",
            "label": "Tenant ID",
            "toolTip": "OAuth2 tenant identifier.",
            "constraints": {
                "required": true,
                "regex": "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
                "validationMessage": "Must be a valid GUID."
            }
        }
    ]
}
```

### Username/Password (Basic Auth)

```json
{
    "name": "credentials",
    "label": "Credentials",
    "elements": [
        {
            "name": "username",
            "type": "Microsoft.Common.TextBox",
            "label": "Username",
            "toolTip": "API username.",
            "constraints": {
                "required": true
            }
        },
        {
            "name": "password",
            "type": "Microsoft.Common.PasswordBox",
            "label": {
                "password": "Password",
                "confirmPassword": "Confirm Password"
            },
            "toolTip": "API password.",
            "constraints": {
                "required": true
            },
            "options": {
                "hideConfirmation": true
            }
        }
    ]
}
```

### Endpoint URL Input

```json
{
    "name": "connectionConfig",
    "label": "Connection",
    "elements": [
        {
            "name": "apiEndpoint",
            "type": "Microsoft.Common.TextBox",
            "label": "API Endpoint URL",
            "toolTip": "The base URL of the API (e.g., https://api.vendor.com/v2).",
            "placeholder": "https://api.vendor.com/v2",
            "constraints": {
                "required": true,
                "regex": "^https://[^\\s]+$",
                "validationMessage": "Must be a valid HTTPS URL."
            }
        }
    ]
}
```

---

## Complete Sentinel Connector Example

```json
{
    "$schema": "https://schema.management.azure.com/schemas/0.1.2-preview/CreateUIDefinition.MultiVm.json#",
    "handler": "Microsoft.Azure.CreateUIDef",
    "version": "0.1.2-preview",
    "parameters": {
        "config": {
            "isWizard": false,
            "basics": {
                "description": "**Vendor Security** connector for Microsoft Sentinel.\n\nThis data connector ingests security events from the Vendor API.",
                "subscription": {
                    "resourceProviders": [
                        "Microsoft.OperationalInsights"
                    ]
                },
                "location": {
                    "label": "Location",
                    "toolTip": "Select the location for the resources.",
                    "resourceTypes": [
                        "Microsoft.OperationalInsights/workspaces"
                    ]
                }
            }
        },
        "basics": [
            {
                "name": "workspace",
                "type": "Microsoft.Solutions.ResourceSelector",
                "label": "Workspace",
                "resourceType": "Microsoft.OperationalInsights/workspaces",
                "toolTip": "Select the Microsoft Sentinel workspace.",
                "constraints": {
                    "required": true
                }
            }
        ],
        "steps": [
            {
                "name": "connectionConfig",
                "label": "Connection",
                "elements": [
                    {
                        "name": "apiEndpoint",
                        "type": "Microsoft.Common.TextBox",
                        "label": "API Endpoint",
                        "toolTip": "Base URL for the Vendor API.",
                        "constraints": {
                            "required": true,
                            "regex": "^https://[^\\s]+$",
                            "validationMessage": "Must be a valid HTTPS URL."
                        }
                    },
                    {
                        "name": "apiKey",
                        "type": "Microsoft.Common.PasswordBox",
                        "label": {
                            "password": "API Key",
                            "confirmPassword": "Confirm API Key"
                        },
                        "toolTip": "API key from the Vendor admin console.",
                        "constraints": {
                            "required": true
                        },
                        "options": {
                            "hideConfirmation": true
                        }
                    }
                ]
            }
        ],
        "outputs": {
            "workspace-location": "[basics('workspace').location]",
            "workspace": "[basics('workspace').name]",
            "apiEndpoint": "[steps('connectionConfig').apiEndpoint]",
            "apiKey": "[steps('connectionConfig').apiKey]"
        }
    }
}
```

---

## Testing

Test your `createUiDefinition.json` in the Azure Portal sandbox:
https://portal.azure.com/#blade/Microsoft_Azure_CreateUIDef/SandboxBlade

Paste your JSON into the sandbox to preview the deployment UI before publishing.

## Microsoft Docs References

- CreateUiDefinition Overview: https://learn.microsoft.com/azure/azure-resource-manager/managed-applications/create-uidefinition-overview
- UI Elements Reference: https://learn.microsoft.com/azure/azure-resource-manager/managed-applications/create-uidefinition-elements
- Functions Reference: https://learn.microsoft.com/azure/azure-resource-manager/managed-applications/create-uidefinition-functions
- Test Sandbox: https://learn.microsoft.com/azure/azure-resource-manager/managed-applications/test-createuidefinition
