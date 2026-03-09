# dstreefkerk-skills

Personal Claude Code plugins following the [Agent Skills specification](https://agentskills.io/specification) for broad compatibility.

## Plugins

| Plugin | Skill | Description |
|--------|-------|-------------|
| `powershell` | `powershell` | Enterprise PowerShell coding standards — structure, error handling, security, performance, and output patterns |
| `sentinel` | `codeless-connectors` | Complete CCF reference for building Sentinel REST/Push/GCP connector ARM templates, DCRs, KQL transforms, and UI definitions |
| | `kql-expert` | KQL query optimisation, schema validation, and best-practice compliance for Sentinel and M365 Defender detection rules |
| | `sentinel-arm-generator` | Generates deployment-ready Sentinel Analytic Rule ARM templates from KQL queries with MITRE mappings and entity extraction |
| | `sentinel-use-case-documentor` | Documents Sentinel analytics rules as comprehensive SOC use cases from ARM templates or KQL detection queries |
| `cyber` | `cyber-impact-statement` | CISO-level impact statements for security control failures — direct causality, business outcomes, no corporate fluff |
| `tech-researcher` | `research` | Validated technical research pipeline with parallel data gathering, quality-gated critique (8/10 threshold), and automatic revision loop |
| `reflect` | `reflect` | Session review — identifies mistakes, friction, and skill optimisation opportunities |
| `productivity` | `slide-notes` | Structured speaker notes for technical presentations — runbook-style bullets with Q&A, references, timing cues, and transitions |
| | `stream-transcript` | Extracts WebVTT transcripts and detects slide transitions from Microsoft Stream / SharePoint-hosted video recordings |

## Installation

### Claude Code Marketplace

```bash
/plugin marketplace add dstreefkerk/claude-skills
```

Then install individual plugins:

```bash
/plugin install powershell@dstreefkerk-skills
/plugin install sentinel@dstreefkerk-skills
/plugin install cyber@dstreefkerk-skills
/plugin install tech-researcher@dstreefkerk-skills
/plugin install reflect@dstreefkerk-skills
/plugin install productivity@dstreefkerk-skills
```

## Local Development

```bash
claude --plugin-dir ./plugins/sentinel
```
