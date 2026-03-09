# Migrate to Personal Claude Plugin Repo Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Strip the jezweb claude-skills template repo and replace it with Daniel's personal skills packaged as Claude Code plugins.

**Architecture:** Delete all existing jezweb plugins and tools, update repo metadata, then create six new plugins from source skills in `C:\Users\Daniel.Streefkerk\.claude\skills\`, `C:\Users\Daniel.Streefkerk\.claude\agents\`, `C:\Users\Daniel.Streefkerk\.claude\commands\`, and `C:\Repos\agent-sentinel-skills\skills\`.

**Plugins:**

| Plugin | Contents | Source |
|--------|----------|--------|
| `powershell` | skill: `powershell` | `~/.claude/skills/powershell` |
| `sentinel` | skills: `codeless-connectors`, `kql-expert`, `sentinel-arm-generator`, `sentinel-use-case-documentor` | `~/.claude/skills/` + `agent-sentinel-skills/skills/` |
| `cyber` | skill: `cyber-impact-statement` | `~/.claude/skills/cyber-impact-statement` |
| `microsoft` | skill: `stream-transcript` | `~/.claude/skills/stream-transcript` |
| `tech-researcher` | agents: `research-critic`, `deep-research-specialist`; command: `research` | `~/.claude/agents/` + `~/.claude/commands/` |
| `productivity` | skills: `reflect`, `slide-notes` | `~/.claude/skills/` |

**Decisions baked in:**
- `HOW_TO_USE.md` and `README.md` from agent-sentinel-skills are excluded (redundant with SKILL.md)
- `sample_input.*` and `expected_output.*` JSON/MD files ARE included (useful Claude reference material)
- `reference/` renamed to `references/` in codeless-connectors
- `research.md` stays as `commands/` (user-triggered orchestration pipeline, not auto-invokable)
- No PII or hardcoded path issues found — files are safe to commit as-is

---

## Task 1: Strip existing repo content

**Step 1: Remove all existing plugins and tools**

```bash
rm -rf plugins/cloudflare plugins/design-assets plugins/dev-tools plugins/frontend \
       plugins/integrations plugins/shopify plugins/web-design plugins/wordpress \
       plugins/writing tools
```

**Step 2: Verify**

```bash
ls plugins/
# Expected: empty (no output)
```

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: remove all jezweb template plugins and tools"
```

---

## Task 2: Update repo metadata

**Files:** `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `CLAUDE.md`, `README.md`

**Step 1: Rewrite `.claude-plugin/plugin.json`**

```json
{
  "name": "daniel-skills",
  "description": "Daniel Streefkerk's personal Claude Code plugin collection.",
  "version": "1.0.0",
  "author": {
    "name": "Daniel Streefkerk"
  }
}
```

**Step 2: Rewrite `.claude-plugin/marketplace.json`**

```json
[
  {
    "name": "powershell",
    "description": "Enterprise PowerShell coding standards and best practices.",
    "source": "./plugins/powershell",
    "category": "development"
  },
  {
    "name": "sentinel",
    "description": "Microsoft Sentinel skills — Codeless Connector Framework, KQL expertise, ARM template generation, and use case documentation.",
    "source": "./plugins/sentinel",
    "category": "security"
  },
  {
    "name": "cyber",
    "description": "CISO-level cyber GRC impact statements for security control failures.",
    "source": "./plugins/cyber",
    "category": "security"
  },
  {
    "name": "microsoft",
    "description": "Microsoft Stream transcript extraction and slide detection from SharePoint-hosted recordings.",
    "source": "./plugins/microsoft",
    "category": "productivity"
  },
  {
    "name": "tech-researcher",
    "description": "Validated technical research pipeline with parallel data gathering, quality-gated critique (8/10 threshold), and automatic revision loop.",
    "source": "./plugins/tech-researcher",
    "category": "productivity"
  },
  {
    "name": "reflect",
    "description": "Session reflection — review mistakes, friction, and skill optimization opportunities.",
    "source": "./plugins/reflect",
    "category": "productivity"
  },
  {
    "name": "productivity",
    "description": "PowerPoint speaker notes for technical presentations.",
    "source": "./plugins/productivity",
    "category": "productivity"
  }
]
```

**Step 3: Rewrite `CLAUDE.md`**

```markdown
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

\`\`\`
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
\`\`\`

## Local Testing

\`\`\`bash
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
\`\`\`
```

**Step 4: Rewrite `README.md`**

```markdown
# Daniel's Claude Skills

Personal Claude Code plugins.

## Plugins

| Plugin | Skills |
|--------|--------|
| `powershell` | Enterprise PowerShell coding standards |
| `sentinel` | Codeless connectors, KQL expert, ARM generator, use case documentor |
| `cyber` | CISO-level impact statements |
| `microsoft` | Stream transcript extraction & slide detection |
| `tech-researcher` | Validated research pipeline with critique loop |
| `productivity` | Session reflection, PowerPoint speaker notes |

## Testing Locally

\`\`\`bash
claude --plugin-dir ./plugins/sentinel
\`\`\`
```

**Step 5: Commit**

```bash
git add -A
git commit -m "chore: update repo metadata for personal plugin collection"
```

---

## Task 3: Create `powershell` plugin

**Source:** `C:\Users\Daniel.Streefkerk\.claude\skills\powershell\`

**Step 1: Create directories**

```bash
mkdir -p plugins/powershell/.claude-plugin
mkdir -p plugins/powershell/skills/powershell/resources
```

**Step 2: Create `plugins/powershell/.claude-plugin/plugin.json`**

```json
{
  "name": "powershell",
  "description": "Enterprise PowerShell coding standards and best practices.",
  "version": "1.0.0",
  "author": {
    "name": "Daniel Streefkerk"
  }
}
```

**Step 3: Copy files**

```bash
cp "C:/Users/Daniel.Streefkerk/.claude/skills/powershell/SKILL.md" \
   plugins/powershell/skills/powershell/SKILL.md

cp "C:/Users/Daniel.Streefkerk/.claude/skills/powershell/resources/"*.md \
   plugins/powershell/skills/powershell/resources/
```

**Step 4: Verify**

```bash
find plugins/powershell -type f | sort
# Expected: plugin.json + SKILL.md + 7 resource .md files (9 total)
```

**Step 5: Commit**

```bash
git add plugins/powershell/
git commit -m "feat: add powershell plugin"
```

---

## Task 4: Create `sentinel` plugin

**Sources:**
- `C:\Users\Daniel.Streefkerk\.claude\skills\codeless-connectors\` (reference/ renamed to references/)
- `C:\Repos\agent-sentinel-skills\skills\kql-expert\`
- `C:\Repos\agent-sentinel-skills\skills\sentinel-arm-generator\`
- `C:\Repos\agent-sentinel-skills\skills\sentinel-use-case-documentor\`

**Note:** Do NOT copy `HOW_TO_USE.md` or `README.md` from agent-sentinel-skills. DO copy `sample_input.*` and `expected_output.*` files.

**Step 1: Create directories**

```bash
mkdir -p plugins/sentinel/.claude-plugin
mkdir -p plugins/sentinel/skills/codeless-connectors/references
mkdir -p plugins/sentinel/skills/codeless-connectors/scripts
mkdir -p plugins/sentinel/skills/kql-expert/references
mkdir -p plugins/sentinel/skills/kql-expert/scripts
mkdir -p plugins/sentinel/skills/sentinel-arm-generator/references
mkdir -p plugins/sentinel/skills/sentinel-arm-generator/scripts
mkdir -p plugins/sentinel/skills/sentinel-use-case-documentor/references
```

**Step 2: Create `plugins/sentinel/.claude-plugin/plugin.json`**

```json
{
  "name": "sentinel",
  "description": "Microsoft Sentinel skills — Codeless Connector Framework, KQL expertise, ARM template generation, and use case documentation.",
  "version": "1.0.0",
  "author": {
    "name": "Daniel Streefkerk"
  }
}
```

**Step 3: Copy codeless-connectors** (rename `reference/` → `references/`)

```bash
cp "C:/Users/Daniel.Streefkerk/.claude/skills/codeless-connectors/SKILL.md" \
   plugins/sentinel/skills/codeless-connectors/SKILL.md

cp "C:/Users/Daniel.Streefkerk/.claude/skills/codeless-connectors/reference/"*.md \
   plugins/sentinel/skills/codeless-connectors/references/

cp "C:/Users/Daniel.Streefkerk/.claude/skills/codeless-connectors/scripts/"* \
   plugins/sentinel/skills/codeless-connectors/scripts/
```

**Step 4: Fix the internal path reference in codeless-connectors SKILL.md**

After copying, update any `reference/` path references in the SKILL.md to `references/`:

```bash
sed -i 's|(reference/|(references/|g' plugins/sentinel/skills/codeless-connectors/SKILL.md
```

Verify the change:

```bash
grep -n "reference" plugins/sentinel/skills/codeless-connectors/SKILL.md | head -20
# Confirm all internal links now say references/
```

**Step 5: Copy kql-expert**

```bash
SRC="C:/Repos/agent-sentinel-skills/skills/kql-expert"
DEST="plugins/sentinel/skills/kql-expert"

cp "$SRC/SKILL.md" "$DEST/SKILL.md"
cp "$SRC/references/"*.md "$DEST/references/"
cp "$SRC/references/environments.json" "$DEST/references/"
cp "$SRC/scripts/"*.py "$DEST/scripts/"
cp "$SRC/sample_input_analytics_rule.json" "$DEST/"
cp "$SRC/sample_input_query_optimization.json" "$DEST/"
cp "$SRC/sample_input_spl_migration.json" "$DEST/"
cp "$SRC/expected_output_analytics_rule.json" "$DEST/"
cp "$SRC/expected_output_query_optimization.json" "$DEST/"
cp "$SRC/expected_output_spl_migration.json" "$DEST/"
```

**Step 6: Copy sentinel-arm-generator**

```bash
SRC="C:/Repos/agent-sentinel-skills/skills/sentinel-arm-generator"
DEST="plugins/sentinel/skills/sentinel-arm-generator"

cp "$SRC/SKILL.md" "$DEST/SKILL.md"
cp "$SRC/references/"*.md "$DEST/references/"
cp "$SRC/scripts/"*.py "$DEST/scripts/"
cp "$SRC/sample_input.json" "$DEST/"
cp "$SRC/expected_output.json" "$DEST/"
```

**Step 7: Copy sentinel-use-case-documentor**

```bash
SRC="C:/Repos/agent-sentinel-skills/skills/sentinel-use-case-documentor"
DEST="plugins/sentinel/skills/sentinel-use-case-documentor"

cp "$SRC/SKILL.md" "$DEST/SKILL.md"
cp "$SRC/references/"*.md "$DEST/references/"
cp "$SRC/sample_input.json" "$DEST/"
cp "$SRC/expected_output.md" "$DEST/"
```

**Step 8: Verify**

```bash
find plugins/sentinel -type f | sort
# Expected: plugin.json + 4 skills with their files (~40 files total)
```

**Step 9: Commit**

```bash
git add plugins/sentinel/
git commit -m "feat: add sentinel plugin (codeless-connectors, kql-expert, sentinel-arm-generator, sentinel-use-case-documentor)"
```

---

## Task 5: Create `cyber` plugin

**Source:** `C:\Users\Daniel.Streefkerk\.claude\skills\cyber-impact-statement\`

**Step 1: Create directories**

```bash
mkdir -p plugins/cyber/.claude-plugin
mkdir -p plugins/cyber/skills/cyber-impact-statement
```

**Step 2: Create `plugins/cyber/.claude-plugin/plugin.json`**

```json
{
  "name": "cyber",
  "description": "CISO-level cyber GRC impact statements for security control failures with direct causality and business outcomes.",
  "version": "1.0.0",
  "author": {
    "name": "Daniel Streefkerk"
  }
}
```

**Step 3: Copy skill**

```bash
cp "C:/Users/Daniel.Streefkerk/.claude/skills/cyber-impact-statement/SKILL.md" \
   plugins/cyber/skills/cyber-impact-statement/SKILL.md
```

**Step 4: Verify**

```bash
find plugins/cyber -type f | sort
# Expected: plugin.json + SKILL.md (2 files)
```

**Step 5: Commit**

```bash
git add plugins/cyber/
git commit -m "feat: add cyber plugin (cyber-impact-statement)"
```

---

## Task 6: Create `microsoft` plugin

**Source:** `C:\Users\Daniel.Streefkerk\.claude\skills\stream-transcript\`

**Step 1: Create directories**

```bash
mkdir -p plugins/microsoft/.claude-plugin
mkdir -p plugins/microsoft/skills/stream-transcript/references
mkdir -p plugins/microsoft/skills/stream-transcript/scripts
```

**Step 2: Create `plugins/microsoft/.claude-plugin/plugin.json`**

```json
{
  "name": "microsoft",
  "description": "Microsoft Stream transcript extraction and slide detection from SharePoint-hosted video recordings.",
  "version": "1.0.0",
  "author": {
    "name": "Daniel Streefkerk"
  }
}
```

**Step 3: Copy skill files**

```bash
cp "C:/Users/Daniel.Streefkerk/.claude/skills/stream-transcript/SKILL.md" \
   plugins/microsoft/skills/stream-transcript/SKILL.md

cp "C:/Users/Daniel.Streefkerk/.claude/skills/stream-transcript/references/"*.md \
   plugins/microsoft/skills/stream-transcript/references/

cp "C:/Users/Daniel.Streefkerk/.claude/skills/stream-transcript/scripts/"* \
   plugins/microsoft/skills/stream-transcript/scripts/
```

**Step 4: Verify**

```bash
find plugins/microsoft -type f | sort
# Expected: plugin.json + SKILL.md + 2 reference files + 3 script files (7 total)
```

**Step 5: Commit**

```bash
git add plugins/microsoft/
git commit -m "feat: add microsoft plugin (stream-transcript)"
```

---

## Task 7: Create `tech-researcher` plugin

**Sources:**
- `C:\Users\Daniel.Streefkerk\.claude\agents\research-critic.md`
- `C:\Users\Daniel.Streefkerk\.claude\agents\deep-research-specialist.md`
- `C:\Users\Daniel.Streefkerk\.claude\commands\research.md`

**Step 1: Create directories**

```bash
mkdir -p plugins/tech-researcher/.claude-plugin
mkdir -p plugins/tech-researcher/agents
mkdir -p plugins/tech-researcher/commands
```

**Step 2: Create `plugins/tech-researcher/.claude-plugin/plugin.json`**

```json
{
  "name": "tech-researcher",
  "description": "Validated technical research pipeline with parallel data gathering, quality-gated critique (8/10 threshold), and automatic revision loop.",
  "version": "1.0.0",
  "author": {
    "name": "Daniel Streefkerk"
  }
}
```

**Step 3: Copy agents and command**

```bash
cp "C:/Users/Daniel.Streefkerk/.claude/agents/research-critic.md" \
   plugins/tech-researcher/agents/research-critic.md

cp "C:/Users/Daniel.Streefkerk/.claude/agents/deep-research-specialist.md" \
   plugins/tech-researcher/agents/deep-research-specialist.md

cp "C:/Users/Daniel.Streefkerk/.claude/commands/research.md" \
   plugins/tech-researcher/commands/research.md
```

**Step 4: Verify**

```bash
find plugins/tech-researcher -type f | sort
# Expected: plugin.json + 2 agent files + research.md (4 files)
```

**Step 5: Commit**

```bash
git add plugins/tech-researcher/
git commit -m "feat: add tech-researcher plugin (research pipeline + agents)"
```

---

## Task 8: Create `reflect` plugin

**Source:** `C:\Users\Daniel.Streefkerk\.claude\skills\reflect\`

**Step 1: Create directories**

```bash
mkdir -p plugins/reflect/.claude-plugin
mkdir -p plugins/reflect/skills/reflect
```

**Step 2: Create `plugins/reflect/.claude-plugin/plugin.json`**

```json
{
  "name": "reflect",
  "description": "Session reflection — review mistakes, friction, and skill optimization opportunities at session end.",
  "version": "1.0.0",
  "author": {
    "name": "Daniel Streefkerk"
  }
}
```

**Step 3: Copy skill**

```bash
cp "C:/Users/Daniel.Streefkerk/.claude/skills/reflect/SKILL.md" \
   plugins/reflect/skills/reflect/SKILL.md
```

**Step 4: Verify**

```bash
find plugins/reflect -type f | sort
# Expected: plugin.json + SKILL.md (2 files)
```

**Step 5: Commit**

```bash
git add plugins/reflect/
git commit -m "feat: add reflect plugin"
```

---

## Task 9: Create `productivity` plugin

**Source:** `C:\Users\Daniel.Streefkerk\.claude\skills\slide-notes\`

**Step 1: Probe slide-notes structure**

```bash
find "C:/Users/Daniel.Streefkerk/.claude/skills/slide-notes" -type f | sort
# Note any subdirectories (references/, scripts/, assets/)
```

**Step 2: Create directories**

```bash
mkdir -p plugins/productivity/.claude-plugin
mkdir -p plugins/productivity/skills/slide-notes
# Create subdirs if they exist in source (from Step 1)
```

**Step 3: Create `plugins/productivity/.claude-plugin/plugin.json`**

```json
{
  "name": "productivity",
  "description": "PowerPoint speaker notes for technical presentations — runbook-style bullet notes with Q&A, references, and timing cues.",
  "version": "1.0.0",
  "author": {
    "name": "Daniel Streefkerk"
  }
}
```

**Step 4: Copy slide-notes** (adapt based on Step 1 findings)

```bash
cp "C:/Users/Daniel.Streefkerk/.claude/skills/slide-notes/SKILL.md" \
   plugins/productivity/skills/slide-notes/SKILL.md

# Copy any subdirectories found in Step 1, e.g.:
# cp -r "C:/Users/Daniel.Streefkerk/.claude/skills/slide-notes/references/" \
#        plugins/productivity/skills/slide-notes/references/
```

**Step 5: Verify**

```bash
find plugins/productivity -type f | sort
# Expected: plugin.json + SKILL.md at minimum
```

**Step 6: Commit**

```bash
git add plugins/productivity/
git commit -m "feat: add productivity plugin (slide-notes)"
```

---

## Task 10: Final validation

**Step 1: Full file listing**

```bash
find plugins -type f | sort
```

**Step 2: Confirm no jezweb/template content remains**

```bash
grep -r "jezweb\|Jeremy Dawes\|cloudflare\|shopify\|wordpress" \
  plugins/ CLAUDE.md README.md .claude-plugin/ 2>/dev/null
# Expected: no matches
```

**Step 3: Validate all plugin.json files**

```bash
for f in $(find plugins -name "plugin.json"); do
  echo -n "$f: "
  python -m json.tool "$f" > /dev/null && echo "OK" || echo "INVALID JSON"
done
```

**Step 4: Check all SKILL.md files have valid frontmatter**

```bash
for f in $(find plugins -name "SKILL.md"); do
  echo -n "$f: "
  head -1 "$f" | grep -q "^---$" && echo "has frontmatter" || echo "MISSING frontmatter delimiter"
done
```

**Step 5: Final commit if needed**

```bash
git status
# If clean: done
# If dirty: git add -A && git commit -m "chore: final cleanup and validation"
```
