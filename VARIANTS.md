# Research Variant Templates

Generate two HTML variant pages from a consolidated extraction JSON. These are the 80/20 templates that capture the most information with the least loss.

## Data Source

Read the consolidated JSON from `.research/exports/[slug]_consolidated.json`. The JSON contains:

```
{
  "source": "Title",
  "speakers": ["Speaker 1", "Speaker 2"],
  "url": "https://...",
  "key_insights": [{ "rank", "title", "description", "evidence": [], "speakers": [] }],
  "themes": [{ "theme", "frequency" }],
  "challenges": [{ "rank", "title", "description", "evidence": [], "speakers": [] }],
  "solutions_approaches": [{ "rank", "title", "description", "implementation", "evidence": [], "speakers": [] }],
  "action_items": [{ "action", "context", "speaker" }],
  "frameworks_models": [{ "name", "description", "speaker" }],
  "top_quotes": [{ "quote", "speaker", "context" }],
  "external_resources": {
    "tools": [{ "name", "mentioned_by", "context" }],
    "people": [{ "name", "mentioned_by", "context" }],
    "other": [{ "type", "name", "mentioned_by", "context" }]
  },
  "metadata": { "extraction_date", "total_chunks", "source_type" }
}
```

Also read the raw transcript from `.research/sources/[slug].txt` to extract timestamps for Show Notes sections. Parse `[HH:MM:SS]` prefixes from transcript lines.

## Output

Save to `.research/variants/[slug]/`:
- `show-notes.html`
- `cheat-sheet.html`

---

## Template 1: Show Notes

**Purpose:** Podcast/video companion page. Someone reads this alongside or after consuming the source. Optimized for reference, scanning, and bookmarking.

**Layout:** Single-column, max-width 820px, light background (#f5f5f7). Apple Podcasts-inspired design language.

### Required Sections (in order)

1. **Header**
   - Artwork placeholder: 120x120px rounded square, dark gradient background, source initials/abbreviation in gold (#c9a959)
   - Label: "Show Notes" in uppercase tracked text
   - Title: source title, 24px bold
   - Meta line: source name, speakers, approximate duration
   - Summary: 2-3 sentence description of the source content

2. **Key Quotes Callout**
   - Dark background card (#1a1a2e), gold accent
   - 2-column grid of the 4-6 best quotes from `top_quotes`
   - Each quote: italic text, gold left border, speaker attribution below

3. **Timestamped Content Sections**
   - One section per major topic/segment in the source
   - Each has: timestamp badge (monospace, blue #007aff on light blue), section title, bullet list
   - Bullets should: bold key terms, use `<span class="tool-mention">` for tool names, use `<span class="inline-quote">` for inline quotes
   - Derive timestamps from the raw transcript. Group content into 8-12 logical sections
   - If no timestamps available (blogs, PDFs), use numbered sections without timestamp badges

4. **Tools & Resources Grid**
   - Header: "Tools & Resources Mentioned"
   - 2-column grid of resource cards
   - Each card: colored icon (first letter, 30x30 rounded), name (bold), one-line description
   - Pull from `external_resources.tools` and `external_resources.other`

5. **People Referenced Grid** (if `external_resources.people` has entries)
   - Same grid layout as tools, dark icon backgrounds
   - Name, one-line context (how/why referenced)

6. **Speakers/Hosts Section** (if multiple speakers)
   - 2-column cards with avatar circles (initials), name, bio describing their contributions to this source

7. **Topics Tag Cloud**
   - Horizontal flex wrap of rounded pill tags
   - Pull from `themes` array

8. **Footer**
   - Source name, "Show Notes", extraction date

### CSS Guidelines

```
Font: -apple-system system font stack
Background: #f5f5f7
Cards: white, 10px border-radius, 1px solid #e5e5e5
Accent: #007aff (timestamps, bullets)
Gold: #c9a959 (quote callout accents)
Dark: #1a1a2e (quote callout background)
Body text: 13.5px, color #48484a
Headings: #1d1d1f
Muted: #8e8e93
Responsive: single column below 640px
```

---

## Template 2: Cheat Sheet

**Purpose:** Print-and-pin reference card. Maximum information density in minimum space. Designed for landscape printing on a single page.

**Layout:** Two-column grid, max-width 1200px, light background. Compact typography (9-11px). Color-coded sections.

### Required Sections (distributed across 2 columns)

**Left column:**

1. **Tools Table** (blue: #2563eb on #eff4ff)
   - Full table with columns: Tool, What It Does, Key Result
   - Pull from `external_resources.tools` and `solutions_approaches`
   - Every tool/solution mentioned gets a row

2. **Frameworks/Mental Models** (purple: #7c3aed on #f5f3ff)
   - Mini cards with colored left border
   - Each card: bold name, 1-2 line description
   - Pull from `frameworks_models`

3. **Challenges** (rose: #be123c on #fff1f2)
   - Compact key-value pairs: bold label + description
   - Pull from `challenges`

**Right column:**

4. **Key Insights** (orange: #c2410c on #fff7ed)
   - Key-value pairs: bold label + one-line summary
   - Pull from `key_insights` (top 10-12)

5. **Essential Quotes** (green: #15803d on #f0fdf4)
   - Stripped-down quotes, 9px italic, speaker tag in small bold
   - Pull from `top_quotes` (all of them)

6. **Action Items** (teal: #0d9488 on #f0fdfa)
   - Checklist with checkmark pseudo-elements
   - Pull from `action_items`

### Header

- Label badge: "CHEAT SHEET" in blue on light blue, uppercase
- Title: source title, 15px bold
- Meta: speakers, "Reference Card", "Print Landscape"

### CSS Guidelines

```
Font: -apple-system system font stack
Base size: 11px root, sections 9-10px
Background: white
Sections: colored backgrounds with matching borders, 5px border-radius
@page: landscape, 10mm margins
Print: -webkit-print-color-adjust: exact, break-inside: avoid
Responsive: single column below 700px
Two-column grid: gap 12px
Table: 9.5px, dotted borders, left-aligned
Item pairs: key bold #1a1a1a, value muted #555
```

### Column Balance

Aim for roughly equal visual weight in both columns. The tools table and insights list are usually the longest sections. If one column runs significantly longer, move the Challenges section to the shorter column.

---

## Generation Rules

1. **Self-contained HTML.** All CSS inline in a `<style>` tag. No external dependencies. No JavaScript (except Interactive Tabs if added later).
2. **Faithful to data.** Every insight, quote, tool, framework, and action item from the consolidated JSON should appear in at least one template. Don't invent content.
3. **Trim quotes.** Clean up transcript artifacts (double spaces, "um", "uh") but don't change meaning.
4. **Timestamps.** Parse from raw transcript `[HH:MM:SS]` lines. Use `MM:SS` format in display. If source has no timestamps, use section numbers.
5. **Speaker handling.** If single speaker, omit the Hosts section and speaker attributions on quotes. If no speakers identified, use "Source" as attribution.
6. **Print testing.** The Cheat Sheet should render cleanly when printed to PDF in landscape mode from Chrome.
