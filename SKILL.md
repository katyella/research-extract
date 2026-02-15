---
name: research-extract
description: >-
  Ingest and analyze content from YouTube, podcasts, blogs, PDFs, and audio files.
  Extract structured insights using parallel agent teams. Optionally generate
  slideshow PDFs. Use /research-extract when you want to analyze any content source
  and extract key insights, quotes, themes, challenges, solutions, frameworks,
  and external resources.
---

# Research Extract

Ingest content from various sources and extract structured insights using parallel agent team processing.

## First-Time Setup

Run once to install Python dependencies:

```bash
bash .claude/skills/research-extract/scripts/setup.sh
```

This creates a virtual environment and installs WeasyPrint, Jinja2, PyYAML, and markdown. It also checks for system dependencies (yt-dlp, pdftotext, whisper).

## Commands

When the user invokes this skill, determine their intent:

### Ingest Commands
- "ingest [url]" or "add [url]" → Ingest a new source
- "ingest [url] as [slug]" → Ingest with custom slug name
- "ingest [filepath]" → Ingest a local file (text, PDF, audio)

### Analysis Commands
- "analyze [slug]" or "extract from [slug]" → Run full extraction with agent team
- "analyze [url] as [slug]" → Ingest AND run extraction in one step

### Slideshow Commands
- "slides [slug]" or "slideshow [slug]" → Generate presentation PDF from consolidated results

### Query Commands
- "list sources" → Show all ingested sources
- "show [slug]" → Show source details and extractions
- "progress" → Check extraction progress

---

## Source Naming

Always use descriptive slugs, not numeric IDs.

When ingesting, derive or ask for a slug:
- YouTube: `mfm-6-ideas`, `lex-altman-interview`
- Blog: `paul-graham-founder-mode`
- File: use filename without extension

The slug is used for all file paths and database lookups.

---

## Parallel Extraction Workflow

This is the core workflow for extracting insights from content.

### Step 1: Ingest the source

```bash
python3 .claude/skills/research-extract/scripts/ingest.py "[URL_OR_PATH]" --slug [SLUG]
```

This will:
- Auto-detect source type (YouTube, blog, PDF, text, audio)
- Download captions or transcribe with Whisper
- Store in `.research-extract/research.db`

### Step 2: Chunk the transcript

```bash
python3 .claude/skills/research-extract/scripts/extract.py chunk --slug [SLUG]
```

This will:
- Split transcript into ~15k character chunks
- Save chunks to `.research-extract/chunks/[slug]_chunk_N.json`
- Initialize progress tracking
- Report number of chunks created

### Step 3: Create team and spawn teammates

Create an Agent Team to coordinate parallel extraction:

**3a. Create the team:**
```
TeamCreate with team_name: "extract-[SLUG]"
```

**3b. Create tasks** - one task per chunk. This lets teammates self-balance workload:
```
For a transcript with 6 chunks, create 6 tasks:

TaskCreate: "Extract chunk 0 for [SLUG]"
TaskCreate: "Extract chunk 1 for [SLUG]"
...
TaskCreate: "Extract chunk 5 for [SLUG]"
```

Each task description should include the full processing instructions (see teammate prompt below).

**3c. Spawn 3 teammates** in a SINGLE message (parallel tool calls):

```
Task tool (x3) with:
  team_name: "extract-[SLUG]"
  name: "extractor-1" / "extractor-2" / "extractor-3"
  subagent_type: "general-purpose"
```

**Teammate prompt template:**
```
You are an extraction teammate on team "extract-[SLUG]".

Your workflow:
1. Check TaskList for pending tasks with no owner
2. Claim a task using TaskUpdate (set owner to your name, status to in_progress)
3. Process the chunk:
   a. Read chunk: python3 .claude/skills/research-extract/scripts/process_chunk.py show --slug [SLUG] --chunk-id [CHUNK_ID]
   b. Analyze the content for: key insights, notable quotes, themes, challenges, solutions/approaches, action items, frameworks/models, and external resources
   c. Save result: python3 .claude/skills/research-extract/scripts/process_chunk.py save --slug [SLUG] --chunk-id [CHUNK_ID] --result '<json>'
4. Mark task completed via TaskUpdate
5. Check TaskList again - claim the next pending task
6. Repeat until no pending tasks remain

JSON format for save:
{
  "chunk_id": X,
  "key_insights": [
    {"title": "...", "description": "...", "speaker": "Name", "quote": "...", "significance": "..."}
  ],
  "quotes": [
    {"quote": "...", "speaker": "Name", "context": "..."}
  ],
  "themes": ["theme1", "theme2"],
  "challenges": [
    {"title": "...", "description": "...", "speaker": "Name", "quote": "..."}
  ],
  "solutions_approaches": [
    {"title": "...", "description": "...", "speaker": "Name", "implementation": "...", "quote": "..."}
  ],
  "action_items": [
    {"action": "...", "context": "...", "speaker": "Name"}
  ],
  "frameworks_models": [
    {"name": "...", "description": "...", "speaker": "Name", "quote": "..."}
  ],
  "external_resources": [
    {"type": "book|podcast|tool|person|course|website|other", "name": "...", "author": "...", "speaker": "who mentioned", "context": "...", "quote": "..."}
  ]
}

IMPORTANT: Capture ALL external resources - books, people referenced/quoted, tools, platforms, podcasts, courses, frameworks.
Work autonomously. Claim tasks, process them, move to next. Stop when no tasks remain.
```

**IMPORTANT:**
- Create 1 task per chunk (teammates self-balance by claiming work)
- Spawn ALL teammates in a SINGLE message (parallel tool calls)
- Use `subagent_type="general-purpose"` and `team_name="extract-[SLUG]"`
- 3 teammates is the default; adjust only for very small (1-2 chunks = 1 teammate) or very large (15+ chunks = 5 teammates) jobs

### Step 4: Wait for completion

Teammates send automatic idle notifications as they finish work. Check progress via:
```
TaskList - shows task completion status across all teammates
```

Fallback:
```bash
python3 .claude/skills/research-extract/scripts/extract.py progress
```

### Step 5: Merge results and clean up team

Once all tasks show completed in TaskList:

**5a. Merge results:**
```bash
python3 .claude/skills/research-extract/scripts/extract.py merge --slug [SLUG]
```
This combines all chunk extractions into `.research-extract/exports/[slug]_merged.json`

**5b. Shut down teammates:**
```
SendMessage type: "shutdown_request" to extractor-1
SendMessage type: "shutdown_request" to extractor-2
SendMessage type: "shutdown_request" to extractor-3
```

**5c. Clean up team:**
```
TeamDelete
```

### Step 6: Consolidate and rank

After merging, create a consolidated analysis that:
- Deduplicates similar insights, challenges, and solutions
- Ranks by frequency/importance
- Identifies top quotes
- Groups external resources by type
- Counts theme frequency

Save to `.research-extract/exports/[slug]_consolidated.json` with this structure:

```json
{
  "source": "Source title",
  "speakers": ["Speaker 1", "Speaker 2"],
  "url": "https://...",

  "key_insights": [
    {
      "rank": 1,
      "title": "Insight title",
      "description": "Synthesized description",
      "evidence": ["quote 1", "quote 2"],
      "speakers": ["Speaker 1"]
    }
  ],

  "themes": [
    {"theme": "Theme name", "frequency": 5}
  ],

  "challenges": [
    {
      "rank": 1,
      "title": "Challenge title",
      "description": "What the challenge is",
      "evidence": ["quote"],
      "speakers": ["Speaker 1"]
    }
  ],

  "solutions_approaches": [
    {
      "rank": 1,
      "title": "Solution title",
      "description": "What it is",
      "implementation": "How to do it",
      "evidence": ["quote"],
      "speakers": ["Speaker 1"]
    }
  ],

  "action_items": [
    {"action": "What to do", "context": "Why", "speaker": "Who"}
  ],

  "frameworks_models": [
    {"name": "Framework name", "description": "How it works", "speaker": "Who"}
  ],

  "top_quotes": [
    {
      "quote": "...",
      "speaker": "...",
      "context": "Why this quote matters"
    }
  ],

  "external_resources": {
    "books": [
      {"title": "Book Title", "author": "Author", "mentioned_by": "Speaker", "context": "Why referenced"}
    ],
    "people": [
      {"name": "Person Name", "mentioned_by": "Speaker", "context": "Why referenced"}
    ],
    "tools": [
      {"name": "Tool Name", "mentioned_by": "Speaker", "context": "How used"}
    ],
    "other": [
      {"type": "podcast|course|website|framework", "name": "...", "mentioned_by": "Speaker", "context": "..."}
    ]
  },

  "metadata": {
    "extraction_date": "2025-01-01T00:00:00",
    "total_chunks": 6,
    "source_type": "youtube"
  }
}
```

### Step 7: Generate slideshow (optional)

If the user requests slides:

```bash
python3 .claude/skills/research-extract/scripts/slideshow.py generate --slug [SLUG]
```

Output: `.research-extract/slides/[slug]-slides.pdf`

The slideshow includes:
1. Title slide (source, speakers, date)
2. Themes overview (card grid)
3. Key insight slides (top insights with descriptions and quotes)
4. Quote slides (large typography, top 3 quotes)
5. Challenges & Solutions (two-column layout)
6. Frameworks slide (if any extracted)
7. Action items slide (if any extracted)
8. Resources slide (grouped by type)

### Step 8: Present summary to user

Show:
- Source slug and title
- Key insights found (ranked)
- Challenges and solutions found (ranked)
- Key themes with frequency
- Top 3-5 quotes
- External resources mentioned (books, people, tools, etc.)
- Links to generated files

---

## Storage Locations

All data stored in `{project_root}/.research-extract/`:

- **Database**: `research.db`
- **Raw transcripts**: `sources/[video_id].txt`
- **Chunks**: `chunks/[slug]_chunk_N.json`
- **Chunk results**: `exports/[slug]_chunk_N_result.json`
- **Merged results**: `exports/[slug]_merged.json`
- **Consolidated**: `exports/[slug]_consolidated.json`
- **Progress**: `extraction_progress.json`
- **Slideshows**: `slides/[slug]-slides.pdf`

---

## For Queries

List sources:
```bash
python3 -c "
import sys; sys.path.insert(0, '.claude/skills/research-extract/scripts')
from db import list_sources
for s in list_sources():
    print(f'{s[\"slug\"]}: [{s[\"source_type\"]}] {s[\"title\"]}')"
```

Get source details:
```bash
python3 -c "
import sys; sys.path.insert(0, '.claude/skills/research-extract/scripts')
from db import get_source_by_slug
source = get_source_by_slug('[SLUG]')
print(f'Title: {source[\"title\"]}')
print(f'Type: {source[\"source_type\"]}')"
```

---

## Tips

- Always use Agent Teams for large transcripts (>20k chars)
- 3 teammates is the default; scale to 1 for tiny jobs (1-2 chunks) or 5 for large (15+ chunks)
- Create 1 task per chunk, teammates self-balance by claiming work from TaskList
- Merge deduplicates overlapping insights automatically
- Consolidation step is where ranking and synthesis happens
- Slideshow generation requires the consolidation step to complete first
- Always shut down teammates and call TeamDelete after merging
