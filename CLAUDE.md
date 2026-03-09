# Daniel's Claude Skills

Personal Claude Code plugin repo — skills, agents, and commands packaged for portability.

## Plugins

| Plugin | Contents | Category |
|--------|----------|----------|
| `powershell` | skill: `powershell` | development |
| `sentinel` | skills: `codeless-connectors`, `kql-expert`, `sentinel-arm-generator`, `sentinel-use-case-documentor` | security |
| `cyber` | skill: `cyber-impact-statement` | security |
| `microsoft` | skill: `stream-transcript` | productivity |
| `tech-researcher` | agents: `research-critic`, `deep-research-specialist`; command: `research` | productivity |
| `reflect` | skill: `reflect` | productivity |
| `productivity` | skill: `slide-notes` | productivity |

## Directory Structure

```
claude-skills/
├── plugins/
│   ├── powershell/
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/powershell/
│   │       ├── SKILL.md
│   │       └── resources/
│   ├── sentinel/
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/
│   │       ├── codeless-connectors/
│   │       ├── kql-expert/
│   │       ├── sentinel-arm-generator/
│   │       └── sentinel-use-case-documentor/
│   ├── cyber/
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/cyber-impact-statement/
│   ├── microsoft/
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/stream-transcript/
│   ├── tech-researcher/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── agents/
│   │   │   ├── research-critic.md
│   │   │   └── deep-research-specialist.md
│   │   └── commands/
│   │       └── research.md
│   ├── reflect/
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/reflect/
│   └── productivity/
│       ├── .claude-plugin/plugin.json
│       └── skills/slide-notes/
├── .claude-plugin/
│   ├── marketplace.json
│   └── plugin.json
└── CLAUDE.md
```

## Local Testing

```bash
# Test a single plugin
claude --plugin-dir ./plugins/sentinel

# Test all plugins
claude \
  --plugin-dir ./plugins/powershell \
  --plugin-dir ./plugins/sentinel \
  --plugin-dir ./plugins/cyber \
  --plugin-dir ./plugins/microsoft \
  --plugin-dir ./plugins/tech-researcher \
  --plugin-dir ./plugins/reflect \
  --plugin-dir ./plugins/productivity
```
