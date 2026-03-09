# dstreefkerk-skills

Personal Claude Code plugins following the [Agent Skills specification](https://agentskills.io/specification) for broad compatibility.

## Plugins

| Plugin | Skills |
|--------|--------|
| `powershell` | Enterprise PowerShell coding standards |
| `sentinel` | Codeless connectors, KQL expert, ARM generator, use case documentor |
| `cyber` | CISO-level impact statements |
| `tech-researcher` | Validated research pipeline with critique loop |
| `reflect` | Session reflection |
| `productivity` | PowerPoint speaker notes, Stream transcript extraction & slide detection |

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
