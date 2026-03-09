---
name: slide-notes
description: Generate structured PowerPoint speaker notes for technical presentations. Produces runbook-style bullet notes (not scripts) that add depth beyond the slide content, including anticipated Q&A, references, emphasis cues, transitions, and time markers. Use when the user asks to write, generate, create, or improve speaker notes, presentation notes, slide notes, or PowerPoint notes. Also triggers when users provide slide content and ask for notes to accompany it. Optimised for cyber security and technical audiences but applicable to any domain.
---

# Slide Notes

Generate structured, scannable speaker notes for PowerPoint slides. Notes function as a presenter's runbook — not a script to be read aloud.

## Workflow

1. Gather the slide content (title, bullets, diagrams) from the user
2. Read [references/slide-notes-guidance.md](references/slide-notes-guidance.md) for the full methodology
3. Generate notes following the structure below
4. Present notes to the user for review

## Notes Structure Per Slide

For each slide, produce notes using these sections. Omit sections that don't apply.

### Core talking points

* Short bullet prompts capturing what to say — key phrases, not full sentences
* Technical nuance not on the slide (caveats, edge cases, assumptions, version dependencies)
* Never duplicate slide text verbatim

### Anticipated questions

* Likely objections or "yes, but what about..." challenges
* Common misconceptions to address
* Trade-offs and constraints worth having ready

### References

* Data sources, report names, CVE numbers, RFC references
* Links to research (even if not shown on slide)
* Keep concise — just enough to avoid "I'll check that later"

### Delivery cues

* Emphasis markers (e.g. "Stress this is detection, not prevention")
* Pace cues ("Pause here", "Slow down for diagram")
* Storytelling flags where a narrative or real-world example fits

### Transition

* Why this slide follows the previous one
* The thread being carried forward
* What the audience should now understand before moving on

### Time and pacing (when presentation has a fixed slot)

* Target time marker for this slide
* Whether the slide is optional / can compress
* What to skip if running short

### Demo guardrails (only for demo slides)

* Exact command syntax
* Expected output
* Fallback if demo fails
* What to cut if time-compressed

## Formatting Rules

* Use short bullets, not paragraphs
* Use sub-bullets for supporting detail
* Use visual markers for emphasis (e.g. bold for strong statements)
* Keep spacing clean — optimise for fast scanning under pressure
* Never include content that would be embarrassing if notes are accidentally shared or exported

## Example

Slide title: "SPF is not an anti-spoofing control"

Example notes output:

```text
CORE TALKING POINTS
- Explain SPF alignment vs envelope sender — most people conflate these
- SPF alone does not prevent display-name spoofing
- DMARC is the dependency that makes SPF useful for anti-spoofing
- Forwarding breaks SPF — common in M365 shared mailbox scenarios

ANTICIPATED QUESTIONS
- "We have SPF set up, aren't we covered?" — No, without DMARC in enforce
  mode SPF results are advisory only
- "What about DKIM?" — Complementary, survives forwarding, but separate
  topic on next slide

REFERENCES
- RFC 7208 (SPF), RFC 7489 (DMARC)
- Proofpoint 2024 email threat report — 87% of spoofed emails pass SPF

DELIVERY CUES
- STRESS that SPF is a building block, not a control in isolation
- Pause after explaining the forwarding breakage — this is the "aha" moment

TRANSITION
- Moves from "what doesn't work alone" to "what does work when layered"
  — next slide covers DMARC enforcement
```
