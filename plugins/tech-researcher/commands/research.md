# /research - Validated Technical Research Pipeline

**Comprehensive research with automated quality control. Produces publication-ready documentation through iterative critique and revision.**

---

## Usage

```
/research [topic]
/research [topic] --quick
/research [topic] --standard
```

---

## Depth Levels

| Flag | Level | Searches | Output | Use When |
|------|-------|----------|--------|----------|
| `--quick` | 1 | 8-12 | 1500-2500 words | Quick overview needed |
| `--standard` | 2 | 15-25 | 3500-5000 words | Moderate depth |
| *(default)* | 3 | 30-50 | 6000-10000 words | Comprehensive analysis |

---

## Pipeline Execution Protocol

When this command is invoked, follow this exact sequence:

### Step 1: Confirm Depth Level

**If no depth flag was provided** (e.g., user just said `/research [topic]`), use AskUserQuestion to ask:

```
AskUserQuestion:
  question: "What depth of research do you need?"
  header: "Depth"
  options:
    - label: "Expert-Level (Recommended)"
      description: "30-50 searches, 6000-10000 words, comprehensive coverage"
    - label: "Standard"
      description: "15-25 searches, 3500-5000 words, solid coverage"
    - label: "Quick Overview"
      description: "8-12 searches, 1500-2500 words, high-level summary"
```

Map the response:
- "Expert-Level" → depth level 3
- "Standard" → depth level 2
- "Quick Overview" → depth level 1

**If a depth flag was provided** (`--quick`, `--standard`), skip this step and use the specified depth.

### Step 2: Announce Pipeline Start

```
Starting validated research pipeline for: [topic]

Pipeline stages:
1. Deep research ([depth-description], [search-count] searches)
2. Critical review with source verification
3. Revision if needed (up to 3 rounds)
4. Final validated document

Proceeding with Stage 1...
```

### Step 3: Preliminary Investigation (Single Agent)

First, invoke one agent to perform preliminary investigation only:

```
Task tool parameters:
- subagent_type: "deep-research-specialist"
- prompt: "Perform PRELIMINARY INVESTIGATION ONLY for: [TOPIC]

           Do NOT proceed to deep research yet. Only complete Stage 1:

           1. Perform 5-8 initial web searches to understand the topic landscape
           2. Identify authoritative sources (vendors, creators, standards bodies)
           3. Discover major concepts, related technologies, and domain classification
           4. Find official documentation URLs

           OUTPUT FORMAT - Return exactly this structure:

           ## Preliminary Investigation Results

           **Topic**: [topic]
           **Domain**: [Security/Development/Infrastructure/etc.]

           ### Research Dimensions Identified
           1. [Dimension 1 name] - [brief description]
           2. [Dimension 2 name] - [brief description]
           3. [Dimension 3 name] - [brief description]
           [up to 5-6 dimensions]

           ### Authoritative Sources
           - [Source 1]: [URL] - [why authoritative]
           - [Source 2]: [URL] - [why authoritative]
           - [Source 3]: [URL] - [why authoritative]

           ### Key Concepts Discovered
           - [concept 1]
           - [concept 2]
           - [concept 3]

           STOP after outputting this. Do not write the full research document."
```

Wait for preliminary investigation to complete. Parse the **Research Dimensions Identified** section.

### Step 3.5: Blind Spot Detection

After preliminary investigation completes, invoke a blind spot detector to identify gaps:

```
Task tool parameters:
- subagent_type: "deep-research-specialist"
- prompt: "BLIND SPOT ANALYSIS for research on: [TOPIC]

           Review the preliminary investigation results:
           [Paste dimensions and sources from Step 3]

           Identify what's MISSING by checking for:

           1. MISSING PERSPECTIVES:
              - If this is a Development topic: Security implications? Performance? Testing?
              - If this is a Security topic: Compliance requirements? Cost of implementation?
              - If this is an Infrastructure topic: Cost? Disaster recovery? Monitoring?
              - Cross-domain concerns often missed?

           2. UNEXPLORED ALTERNATIVES:
              - Are there competing tools/approaches not mentioned?
              - Open source vs commercial options?
              - Legacy vs modern approaches?
              - Different methodologies or frameworks?

           3. EDGE CASES AND GOTCHAS:
              - Common failure scenarios?
              - Scale limitations?
              - Integration challenges?
              - Migration/adoption pitfalls?

           Perform 3-5 targeted searches to verify blind spots exist.

           OUTPUT FORMAT:
           ## Blind Spots Identified

           ### Additional Dimensions to Research
           1. [Blind spot 1] - [why this matters]
           2. [Blind spot 2] - [why this matters]
           [only include genuine gaps, not padding]

           ### No Blind Spots Found In
           - [Area checked but adequately covered]

           If no significant blind spots found, state: 'Preliminary investigation appears comprehensive.'"
```

Wait for blind spot analysis to complete. Add any **Additional Dimensions to Research** to the dimensions list from Step 3.

### Step 4: Parallel Data Gathering (Multiple Agents)

Launch **concurrent** Task agents for each research dimension in **DATA GATHERING MODE**. This includes:
- Original dimensions identified in Step 3 (Preliminary Investigation)
- Additional dimensions from Step 3.5 (Blind Spot Detection)

**CRITICAL**: Agents produce **structured Data Packages**, NOT prose. The prose synthesis happens in Step 5.

**CRITICAL**: Send a SINGLE message with MULTIPLE Task tool calls to run in parallel:

```
For each dimension (from Step 3 + Step 3.5), invoke:

Task tool parameters:
- subagent_type: "deep-research-specialist"
- prompt: "MODE: DATA GATHERING

           Dimension: [DIMENSION NAME]
           Context: This is part of broader research on [MAIN TOPIC].

           Authoritative sources to prioritize (from preliminary investigation):
           - [Source 1]
           - [Source 2]

           INSTRUCTIONS:
           1. Skip preliminary investigation (already done)
           2. Perform 8-15 targeted searches on this specific dimension
           3. Use Tier 1-4 source hierarchy
           4. Cross-reference findings
           5. Output ONLY a structured Data Package (no prose narrative)

           OUTPUT FORMAT - Data Package:

           ## Data Package: [Dimension Name]

           ### Key Findings
           1. **[Finding title]**: [Factual statement with specifics]
           2. **[Finding title]**: [Factual statement with specifics]
           [5-10 key findings]

           ### Supporting Evidence
           | Claim | Quote/Evidence | Source | Tier |
           |-------|----------------|--------|------|
           | [Claim] | \"[Direct quote]\" | [URL] | 1 |
           [Include all major claims with sources]

           ### Code/Configuration Examples
           [Include relevant code snippets with context]

           ### Anti-Patterns Identified
           | Anti-Pattern | Why It's Wrong | Better Approach |
           |--------------|----------------|-----------------|
           | [Pattern] | [Explanation] | [Alternative] |

           ### Sources Consulted
           - **Tier 1**: [URL] - [What was found]
           - **Tier 2**: [URL] - [What was found]

           ### Gaps/Uncertainties
           - [Any areas where information was thin or conflicting]

           Do NOT write to file. Return the Data Package directly."
```

**Example**: If Step 3 identified 4 dimensions and Step 3.5 added 2 blind spot dimensions, send ONE message with 6 Task tool calls running in parallel.

Wait for ALL parallel agents to complete. **Store all Data Packages** - they will be passed to the Lead Author and may be needed for revision.

### Step 5: Lead Author Synthesis

After all parallel data gathering agents complete, invoke a **single Lead Author agent** to synthesize the Data Packages into a cohesive document.

**CRITICAL**: Do NOT simply concatenate the Data Packages. The Lead Author creates unified prose with consistent voice.

```
Task tool parameters:
- subagent_type: "deep-research-specialist"
- prompt: "MODE: LEAD AUTHOR

           Topic: [MAIN TOPIC]
           Domain: [Domain from Step 3 - Security/Development/Infrastructure/etc.]

           RESEARCH BRIEF (from preliminary investigation):
           [Paste the key findings from Step 3]

           DATA PACKAGES TO SYNTHESIZE:
           [Paste ALL Data Packages from Step 4 - include complete content]

           INSTRUCTIONS:
           1. DO NOT perform additional web searches - all data has been gathered
           2. Synthesize the Data Packages into a single cohesive document
           3. Ensure consistent voice and logical flow throughout
           4. Create smooth transitions between sections
           5. Eliminate redundancy - introduce concepts once, then reference
           6. Cross-reference between sections where concepts connect
           7. Preserve ALL anti-patterns and gotchas from the Data Packages
           8. Retain ALL source citations with proper attribution

           STRUCTURE TEMPLATE (adapt based on domain):

           # [TOPIC] - Comprehensive Research

           ## Executive Summary
           [Opening insight - the single most important finding, NOT 'This document...']

           **Key Takeaways:**
           - [Actionable takeaway 1]
           - [Actionable takeaway 2]
           - [Actionable takeaway 3]

           [1-2 sentences on business/security/operational impact]

           ---

           ## Table of Contents
           [Generated from sections]

           ## [Section 1 - synthesized from relevant Data Packages]
           [Cohesive prose with inline citations]

           ## [Section 2 - synthesized from relevant Data Packages]
           [Cohesive prose with inline citations]

           ## Anti-Patterns and Common Mistakes
           [Consolidated from all Data Packages, organized logically]

           ## Authoritative Sources
           ### Tier 1: Vendor & Creator Resources
           [Consolidated and deduplicated]
           ### Tier 2: Standards & Academic
           [Consolidated and deduplicated]
           ### Tier 3-4: Industry & Community
           [Consolidated and deduplicated]

           QUALITY STANDARDS:
           - No section should read like it was written by a different author
           - Transitions between major sections must feel natural
           - The document should tell a coherent story, not present disconnected facts
           - DO NOT start Executive Summary with 'This document/research/guide...'
           - DO NOT include internal metadata (search counts, word counts, depth levels)

           Write the complete document to [topic-kebab-case]-research.md"
```

Wait for the Lead Author to complete. The output is the first draft of the research document.

### Step 6: Verify Research Output

After merge and synthesis completes:
1. Use Read tool to confirm the research document exists
2. Note the file path for the critique stage
3. Announce completion

```
Research complete. Document created: [filename]
Dimensions researched: [N] (in parallel)

Proceeding to Critical Review...
```

### Step 7: Invoke Research Critic

Use the Task tool to invoke the critic agent:

```
Task tool parameters:
- subagent_type: "research-critic"
- prompt: "Review the research document at [filepath].
           Provide a comprehensive critique using your standard rubric.
           You MUST use WebFetch to verify at least 2 Tier 1 sources cited.
           Focus on source integrity, depth, logic gaps, formatting, and anti-pattern accuracy.
           Start from a baseline of 6/10 and adjust based on evidence.
           You must find at least 3 issues."
```

**CRITICAL**: The `research-critic` agent has these tools: Read, Grep, WebFetch. It MUST use WebFetch to verify sources.

### Step 8: Parse Critique and Quality Gate

After the critic completes:
1. Extract the overall score (X/10)
2. Identify all critical flaws
3. Store the FULL critique text (do not summarize)

**Quality Gate Decision**:

| Score | Action |
|-------|--------|
| 8-10 | PASSED - Deliver final document |
| 6-7 | REVISION NEEDED - Proceed to Step 9 |
| 0-5 | MAJOR ISSUES - Proceed to Step 9 with warning |

### Step 9: Reviser Agent (If Needed)

For each revision round (max 3), invoke the **Reviser agent** to produce a complete revised document:

```
Task tool parameters:
- subagent_type: "deep-research-specialist"
- prompt: "MODE: REVISER

           Topic: [MAIN TOPIC]

           CURRENT DRAFT:
           [Read and paste the full current research document]

           FULL CRITIQUE:
           [Paste the COMPLETE critique from research-critic - all flaws, all locations]

           ORIGINAL DATA PACKAGES (for reference):
           [Paste all Data Packages from Step 4]

           INSTRUCTIONS:
           1. Read the critique carefully - address EVERY point raised
           2. Produce a COMPLETE new document (not patches or diffs)
           3. Maintain the document's voice and structure while fixing issues
           4. For 'depth gaps': use original Data Packages to add detail
           5. For 'contradictions': resolve with explanation or remove conflict
           6. For 'missing citations': add from Data Packages or note as unverifiable
           7. If critique contains [REQUIRES RE-GATHERING] markers, note them in your output

           PRIORITY HANDLING:
           - Critical Flaws: MUST be fully resolved
           - Suggestions for Depth: Address if data exists in packages

           AFTER REVISION, list:
           ## Revision Summary
           - [Flaw 1]: [How it was addressed]
           - [Flaw 2]: [How it was addressed]
           - Re-gathering needed: [Yes/No - list sections if yes]

           Write the complete revised document to [topic-kebab-case]-research.md"
```

After the Reviser completes, check for **[REQUIRES RE-GATHERING]** markers in the critique or Reviser output.

### Step 9.5: Adaptive Re-Gathering (If Needed)

If the critique contained **[REQUIRES RE-GATHERING]** markers:

1. **Parse the re-gathering requirements**:
   - Extract the section names flagged
   - Extract the suggested search queries
   - Note what type of sources are needed

2. **Spawn targeted Data Gathering agents** (max 2 per revision round):

```
Task tool parameters:
- subagent_type: "deep-research-specialist"
- prompt: "MODE: DATA GATHERING

           TARGETED RE-GATHERING for: [Section Name]
           Context: Filling a gap identified during revision of research on [MAIN TOPIC]

           GAP TO FILL:
           [Paste the gap description from critique]

           SUGGESTED SEARCHES:
           [Paste the suggested search queries from critique]

           INSTRUCTIONS:
           1. Perform 5-8 targeted searches on this specific gap
           2. Focus on finding the missing information identified
           3. Output a supplementary Data Package

           OUTPUT FORMAT - Supplementary Data Package:

           ## Supplementary Data Package: [Gap Topic]

           ### Findings That Fill the Gap
           [Structured findings addressing the specific gap]

           ### Supporting Evidence
           [Sources and quotes]

           ### Remaining Uncertainties
           [What still couldn't be found]

           Return the Data Package directly."
```

3. **Feed supplementary Data Packages to Reviser**:
   - Re-invoke the Reviser agent with the new data
   - Include both original Data Packages AND supplementary ones

4. **Return to Step 7** (re-critique the revised document)

**Limits**:
- Maximum 2 re-gathering triggers per critique (enforced by critic)
- Maximum 1 re-gathering cycle per revision round
- If re-gathering still doesn't fill the gap, document as "Information unavailable from authoritative sources"

**Loop Detection**:
- No improvement for 2 rounds → Exit with best version
- Score regression → Revert to higher-scoring version
- After 3 rounds total → Deliver best version with notes

### Step 10: Final Delivery

```markdown
# Research Pipeline Complete

## Summary
- **Topic**: [Topic]
- **Final Score**: X/10
- **Revision Rounds**: N
- **Document**: [filepath]

## Quality Metrics
- Source Integrity: X/10
- Depth: X/10
- Logic Consistency: X/10
- Formatting: X/10
- Anti-Pattern Accuracy: X/10

## Document Location
The validated research document is saved at: `[filepath]`
```

---

## Configuration

| Setting | Value |
|---------|-------|
| **Default Depth** | 3 (Expert-Level) |
| **Quality Threshold** | 8/10 |
| **Max Revision Rounds** | 3 |
| **Minimum Acceptable** | 6/10 |

---

## Agent Tool Reference

| Agent | Tools Available |
|-------|-----------------|
| deep-research-specialist | WebSearch, WebFetch, Read, Write, Glob, Grep |
| research-critic | Read, Grep, WebFetch |

---

## Examples

### Basic Research (Expert-Level by Default)

```
/research Kubernetes network policies
```

### Quick Overview

```
/research GraphQL authentication --quick
```

### Standard Depth

```
/research Azure AD security --standard
```

---

## Troubleshooting

**If WebSearch is not available to the research specialist**:
- Ensure you're invoking via Task tool with `subagent_type: "deep-research-specialist"`
- The agent's tools are defined in its YAML frontmatter in `.claude/agents/`

**If research-critic gives inflated scores**:
- The critic has negative constraints to combat polite bias
- The prompt reminds it: "Start from 6/10 baseline, find at least 3 issues"

**If pipeline loops endlessly**:
- Loop detection exits after no improvement for 2 rounds
- Maximum 3 revision rounds enforced

---

## Bypassing the Pipeline

For **quick, unvalidated** research:
```
Use the deep-research-specialist agent to research [topic]. Skip critique.
```

To **critique existing research**:
```
Use the research-critic agent to review [document-path]
```

---

**Validated research, every time.**
