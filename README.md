# research-extract

Extract structured insights from YouTube videos, podcasts, blogs, PDFs, and audio files using Claude Code's parallel agent teams.

## What it does

Feed it any content source and it will:

1. **Ingest** the content (download captions, transcribe audio, fetch articles)
2. **Chunk** long transcripts into processable pieces
3. **Extract** insights in parallel using agent teams (3 agents processing chunks simultaneously)
4. **Merge and rank** all findings into a consolidated analysis
5. **Generate variants** — Show Notes and Cheat Sheet HTML pages

### What gets extracted

- Key insights with quotes and attribution
- Notable quotes
- Recurring themes with frequency counts
- Challenges and problems discussed
- Solutions and approaches proposed
- Concrete action items
- Frameworks and mental models
- External resources (books, tools, people, podcasts, courses)

## Install

Copy this directory into `.claude/skills/research-extract/` in your project:

```bash
cp -r research-extract/ your-project/.claude/skills/research-extract/
```

### First-time setup

```bash
bash .claude/skills/research-extract/scripts/setup.sh
```

Checks for required system tools (yt-dlp, pdftotext, whisper).

**Required:** `yt-dlp` (for YouTube). Install with `brew install yt-dlp` or `pip install yt-dlp`.

**Optional:** `whisper` (for audio without captions), `pdftotext` (for PDFs).

## Usage

In Claude Code, use the `/research-extract` command:

```
/research-extract ingest https://youtube.com/watch?v=abc123 as my-talk
/research-extract analyze my-talk
/research-extract variants my-talk
/research-extract list sources
```

### Full workflow example

```
> /research-extract ingest https://youtube.com/watch?v=abc123 as startup-advice

Ingested: startup-advice (How to Start a Startup - Sam Altman)
Transcript: 45,231 chars

> /research-extract analyze startup-advice

Chunking... 4 chunks created
Spawning 3 extraction agents...
[################--------------] 50% (2/4 chunks)
...
Extraction complete. Merging results...

Key Insights (ranked):
1. Start with a problem you've experienced personally
2. Talk to users before writing code
...

> /research-extract variants startup-advice

Generated:
  .research-extract/variants/startup-advice/show-notes.html
  .research-extract/variants/startup-advice/cheat-sheet.html
```

## Supported sources

| Source | How |
|--------|-----|
| YouTube | Auto-captions via yt-dlp, Whisper fallback |
| Blog/article URLs | HTML fetch + text extraction |
| Text files (.txt, .md) | Direct read |
| PDF files | pdftotext extraction |
| Audio files (.mp3, .wav, .m4a) | Whisper transcription |

## Data storage

All data lives in `.research-extract/` at your project root (gitignored by default):

```
.research-extract/
├── research.db                        # SQLite database
├── sources/                           # Raw transcripts
├── chunks/                            # Chunked transcript files
├── exports/                           # Extraction results (merged, consolidated)
├── extraction_progress_[slug].json    # Per-slug progress tracking
├── writeups/                          # Generated markdown writeups
└── variants/                          # Generated HTML variant pages
```

## How it works

The extraction pipeline uses Claude Code's agent team feature for parallel processing:

1. Transcript gets split into ~15k character chunks
2. A team of 3 agents is spawned, each claiming and processing chunks from a shared task list
3. Each agent extracts structured data (insights, quotes, themes, etc.) from its chunks
4. Results are merged and deduplicated
5. A consolidation pass ranks everything by importance and frequency

This means a 60-minute podcast (6+ chunks) gets fully analyzed in roughly the time it takes to process 2 chunks sequentially.
