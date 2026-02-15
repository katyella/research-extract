# Research Writeup Style Guide

## Two Output Formats

Every research extraction produces two files:

1. **Notes** (`-notes.md`) — Quick reference, scannable
2. **Writeup** (`-writeup.md`) — Essay-style prose for reading

---

## Notes Format

The notes file is for quick scanning and reference.

### Structure
- Header with source, speakers, date
- Sections matching main topics
- Bullet points, not paragraphs
- Timestamps as clickable links: `[(4:57)](url#t=4m57s)`
- Key quotes in blockquotes with speaker attribution
- Table of best quotes at bottom

### Example
```markdown
## The Shift

- Preference cascade happened around 2024 holidays
- Karpathy said "I feel behind" → social friction evaporated [(3:42)](url#t=3m42s)

> "90% of the code he pushes to production he doesn't even look at."
> — Jordan Gal [(4:57)](url#t=4m57s)
```

---

## Writeup Format (Essay Style)

The writeup is for reading and thinking. It should feel like a well-crafted essay.

### Structure
- **Introduction**: Frame the topic's significance, establish what's at stake
- **Body sections**: Each explores one major theme
- **Conclusion**: Synthesize implications, what this means going forward

### Paragraph Style

Write developed paragraphs, not terse bullets. Each paragraph should:
1. Open with a topic sentence establishing the point
2. Develop the idea with explanation and context
3. Support with evidence (quotes with timestamp citations)
4. Explain why it matters

**Bad (too terse):**
> The cost of engineering mistakes is now near-zero. This changes everything about product process.

**Good (developed):**
> To understand the magnitude of this change, one must first understand how product development traditionally worked and why it worked that way. The process was designed around a fundamental constraint: engineering mistakes were expensive. If a product manager gave incomplete or incorrect requirements, the resulting code would be wrong, and fixing it would consume weeks or months of valuable engineering time. This created enormous pressure to get specifications right before any code was written.

### Quote Integration

Weave quotes into prose with timestamp citations in parentheses:

**Bad:**
> Jordan said: "The cost has gone to near zero."

**Good:**
> Jordan Gal describes the old reality: "If you give the wrong set of requirements... and then it comes back to product and it's not quite right, it's very, very costly" [(13:12)](url#t=13m12s). The response to this reality was a heavy emphasis on upfront specification.

### Quote Accuracy and Consistency

**Quotes must be identical between notes and writeup files.**

1. **Verify against source**: Always check quotes against the original transcript or source material. Do not paraphrase or abbreviate.

2. **Single source of truth**: When writing both files, copy quotes exactly. If a quote appears in the notes as `"You don't need to draw pictures of apps we're gonna build anymore"`, the writeup must use the same text.

3. **Cleaning up spoken language**: Transcripts often include stutters ("That that the the thing"). You may clean these up, but:
   - Clean consistently in both files
   - Preserve the actual words and meaning
   - Do not add or change words

4. **When in doubt, fetch the transcript**: If a quote looks awkward, verify it against the source before assuming it's wrong. Spoken language often sounds awkward when written.

**Bad (inconsistent):**
- Notes: `"You don't need to draw pictures of apps anymore."`
- Writeup: `"You don't need to draw pictures of apps we're gonna build anymore."`

**Good (consistent):**
- Notes: `"You don't need to draw pictures of apps we're gonna build anymore."`
- Writeup: `"You don't need to draw pictures of apps we're gonna build anymore."`

### Connective Tissue

Use transitions between ideas and sections:
- "This matters because..."
- "The implication is..."
- "However, this velocity creates its own problems..."
- "Compounding this challenge is..."
- "To understand this, one must first..."

### Voice

- Analytical but not dry
- Explain significance, don't just report facts
- Connect ideas to broader implications
- Third person, present tense for analysis

### Punctuation

**NEVER use em dashes (—) or double hyphens (--) in text.**

Instead of em dashes, use:
- **Commas** for parenthetical phrases: "The engineer, who was skeptical, finally tried it"
- **Periods** for new sentences: "This was impossible. Not because of skill, but process."
- **Colons** to introduce lists or explanations: "The bottleneck is everything after: docs, marketing, support"
- **"meaning" or "which means"** for clarifying phrases

**Examples:**
- BAD: "traditional engineers—those who write code by hand—still exist"
- GOOD: "traditional engineers, those who write code by hand, still exist"
- BAD: "the constraint has moved—engineering is now faster"
- GOOD: "The constraint has moved. Engineering is now faster."

