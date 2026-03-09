# Claude Code Skills

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Workflow skills for [Claude Code](https://claude.com/claude-code) that produce tangible output. Each skill guides Claude through a recipe — scaffold a project, generate assets, deploy to production.

## Plugins

| Plugin | Skills | What it produces |
|--------|--------|-----------------|
| **cloudflare** | cloudflare-worker-builder, vite-flare-starter, tanstack-start, hono-api-scaffolder, d1-drizzle-schema | Deployable Cloudflare Workers, full-stack apps, TanStack Start SSR dashboards, Hono APIs, D1 schemas |
| **web-design** | web-design-methodology, web-design-patterns, seo-local-business | Production HTML/CSS, component patterns, local business SEO |
| **frontend** | tailwind-theme-builder, shadcn-ui | Themed Tailwind v4 + shadcn/ui setup with dark mode |
| **design-assets** | color-palette, favicon-gen, icon-set-generator, gemini-image-gen, image-processing | Colour palettes, favicons, SVG icons, AI image generation, image processing |
| **integrations** | google-chat-messages, google-apps-script, elevenlabs-agents, mcp-builder | Google Chat webhooks, Apps Script, ElevenLabs agents, MCP servers |
| **dev-tools** | project-health, dev-session, team-update, github-release, gemini-peer-review, gemini-guide, claude-capabilities, ux-audit, responsiveness-check | Project health audits, session tracking, team updates with feedback triage, releases, Gemini peer review, API guide, UX audits, responsive testing |
| **shopify** | shopify-setup, shopify-products, shopify-content | Shopify API setup, product management, content pages, blog posts |
| **wordpress** | wordpress-setup, wordpress-content, wordpress-elementor | WordPress WP-CLI access, content management, Elementor page editing |
| **writing** | aussie-business-english | Australian business English writing style |

## Install

```bash
# Add the marketplace
/plugin marketplace add jezweb/claude-skills

# Install individual plugins
/plugin install cloudflare@jezweb-skills
/plugin install frontend@jezweb-skills
/plugin install dev-tools@jezweb-skills
/plugin install web-design@jezweb-skills
/plugin install design-assets@jezweb-skills
/plugin install integrations@jezweb-skills
/plugin install shopify@jezweb-skills
/plugin install wordpress@jezweb-skills
/plugin install writing@jezweb-skills
```

## Create Your Own

Use [Anthropic's official skill-creator](https://github.com/anthropics/skills) or ask Claude: "Create a new skill for [use case]"

## Philosophy

**Every skill must produce something.** No knowledge dumps — only workflow recipes that create files, projects, or configurations. Claude's training data handles the rest.

See [CLAUDE.md](CLAUDE.md) for development details.

## History

This repo started as a collection of 105 skills — many were informational reference guides (CSS patterns, API docs, framework cheatsheets). With Claude's expanded training data and built-in capabilities, those reference skills became redundant.

**v2** restructured into 7 installable plugins containing 24 skills that produce tangible output. Each one earns its place.

The full v1 collection is preserved and usable:

```bash
# Browse the v1 skills
git log v1-final -- skills/

# Use a specific v1 skill locally
git checkout v1-final -- skills/css-grid/
claude --plugin-dir ./skills/css-grid
```

- **Tag `v1-final`** — all 105 skills at the point of transition
- **Branch `archive/low-priority-skills`** — 13 previously archived skills

## License

MIT
