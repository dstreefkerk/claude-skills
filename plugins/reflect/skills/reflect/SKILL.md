---
name: reflect
description: Review the current chat session to identify mistakes, friction, and unclear outputs. Propose improvements and check any skills used for optimization opportunities. Use when correcting course or at session end.
---

# Reflect

## Success Criteria
1. Session summary is 3-5 bullets, not a wall of text.
2. Every identified issue cites a specific moment (not vague).
3. Every proposed improvement is actionable (starts with a verb, names a specific behavior).
4. User is explicitly asked which items to persist before anything is written.

This is a **multi-turn** skill. Execute each part sequentially, waiting for the user's response to each `AskUserQuestion` before proceeding to the next part. If a part has zero findings or proposals, skip it entirely — do not output "none found."

## Part 1: Session Review

1. **Summarize** what was accomplished in this chat (bullet list, 3-5 items max).
2. **Identify issues** — any of:
   - Mistakes I made (wrong output, bad assumptions, unnecessary work)
   - Friction points (user had to repeat themselves, clarify, or correct me)
   - Unclear or verbose outputs the user had to parse
3. **Propose improvements** — a short numbered list of concrete changes to my behavior (e.g., "Ask before running deploy commands", "Keep plans under 50 lines"). Only include improvements that directly address identified issues; avoid generic suggestions. Each must be actionable and specific.
4. **Present improvements interactively**: Use `AskUserQuestion` with `multiSelect: true`. Each proposed improvement becomes one option (label = short name, description = the full actionable statement). Even if only 1 improvement is proposed, still use `AskUserQuestion` — include a "None of these" option so the user can decline.
5. **Wait for the user's response.** Persist only the selected improvements to CLAUDE.md. Do not write anything if the user selects none.

**Stop here and wait for the user's AskUserQuestion response before continuing to Part 2.**

## Part 2: Skill Audit

Check which skills (files in `.claude/skills/`) were invoked or relevant during this session. If no skills were used or no changes are needed, skip this part entirely.

For each skill used:

### Self-check injection
If the skill lacks Success Criteria or self-verification instructions, propose adding both (2-4 measurable criteria at the top, verification loop at the bottom).

### Token efficiency
Scan the skill for redundancy, over-explanation, or sections that could be shortened without losing clarity or functionality. Focus on: duplicate examples, repeated warnings, verbose sections (>10 lines of similar advice). Propose specific edits with before/after text.

### Other improvements
Note any other issues (stale references, missing edge cases, wrong defaults). Propose fixes.

**Present skill changes interactively**: Output the findings as text, then use `AskUserQuestion` with `multiSelect: true`. Each proposed skill change becomes one option (label = skill name + change type, description = what will be changed). Wait for the user's response, then apply only the selected changes.

**Stop here and wait for the user's AskUserQuestion response before continuing to Part 3.**

## Part 3: Pattern Detection

If the user has asked me to do similar tasks 2+ times in this session (e.g., "format this as a table", "check types then test"), suggest creating a reusable skill for it. If no repeated patterns are found, skip this part entirely.

**Present pattern proposals interactively**: Describe what each proposed skill would do as text, then use `AskUserQuestion` with options for each proposed skill (label = skill name, description = what it automates). Include a "None" option. Wait for the user's response, then create only the confirmed skills.

## Self-Verification
Before presenting output in each part, verify all Success Criteria are met. If any criterion fails, revise and re-check (up to 5 iterations). If after 5 iterations a criterion is still unmet, document which criterion failed, why, and present the best output achievable.
