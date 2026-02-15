"""
Chunk Processor
Called by agents to process individual chunks and extract insights.
Outputs structured JSON that can be merged later.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract import update_progress, CHUNKS_DIR, EXPORTS_DIR, get_progress


def get_chunk(slug: str = None, source_id: int = None, chunk_id: int = 0) -> dict:
    """Load a chunk file by slug or source_id."""
    if slug:
        chunk_path = CHUNKS_DIR / f"{slug}_chunk_{chunk_id}.json"
        if chunk_path.exists():
            with open(chunk_path, 'r') as f:
                return json.load(f)

    if source_id:
        chunk_path = CHUNKS_DIR / f"source_{source_id}_chunk_{chunk_id}.json"
        if chunk_path.exists():
            with open(chunk_path, 'r') as f:
                return json.load(f)

    return None


def save_chunk_result(slug: str = None, source_id: int = None, chunk_id: int = 0, result: dict = None):
    """Save extraction result for a chunk."""
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if slug:
        result_path = EXPORTS_DIR / f"{slug}_chunk_{chunk_id}_result.json"
    else:
        result_path = EXPORTS_DIR / f"source_{source_id}_chunk_{chunk_id}_result.json"

    with open(result_path, 'w') as f:
        json.dump(result, f, indent=2)

    update_progress(chunk_id, "completed", result)
    return result_path


def print_chunk_for_analysis(slug: str = None, source_id: int = None, chunk_id: int = 0):
    """Print chunk content for agent to analyze."""
    chunk = get_chunk(slug=slug, source_id=source_id, chunk_id=chunk_id)
    if not chunk:
        identifier = slug or f"source {source_id}"
        print(f"ERROR: Chunk {chunk_id} not found for {identifier}")
        return

    print(f"=== CHUNK {chunk_id} of {chunk['title']} ===")
    print(f"Characters: {chunk['char_count']}")
    print(f"Start position: {chunk['start_char']}")
    print("=" * 50)
    print(chunk['text'])
    print("=" * 50)


EXTRACTION_PROMPT = """
Analyze this content chunk and extract the following:

1. **Key Insights** - Important ideas, findings, or observations. For each:
   - title: brief descriptive title
   - description: 1-2 sentence summary
   - speaker: who said/presented it
   - quote: exact quote if available
   - significance: why this matters

2. **Notable Quotes** - Memorable, quotable statements worth saving. For each:
   - quote: the exact words
   - speaker: who said it
   - context: what they were discussing

3. **Themes** - Recurring topics or patterns (as simple strings)

4. **Challenges** - Problems, obstacles, or difficulties discussed. For each:
   - title: brief title
   - description: what the challenge is
   - speaker: who raised it
   - quote: exact quote if available

5. **Solutions/Approaches** - Methods, strategies, or fixes discussed. For each:
   - title: brief title
   - description: what the approach is
   - speaker: who proposed it
   - implementation: how to apply it (if discussed)
   - quote: exact quote if available

6. **Action Items** - Concrete takeaways or things to do. For each:
   - action: what to do
   - context: why or when
   - speaker: who suggested it

7. **Frameworks/Models** - Mental models, frameworks, or structured thinking tools. For each:
   - name: framework name
   - description: how it works
   - speaker: who presented it
   - quote: exact quote if available

8. **External Resources** - ANY books, podcasts, tools, people, courses, websites, or other resources mentioned. For each:
   - type: "book" | "podcast" | "tool" | "person" | "course" | "website" | "other"
   - name: title or name of the resource
   - author: author/creator if mentioned
   - speaker: who mentioned it
   - context: why it was mentioned or how it's relevant
   - quote: exact quote mentioning it if available

   IMPORTANT: Capture ALL external references, even brief mentions.

Return as JSON:
{
  "chunk_id": <id>,
  "key_insights": [...],
  "quotes": [...],
  "themes": [...],
  "challenges": [...],
  "solutions_approaches": [...],
  "action_items": [...],
  "frameworks_models": [...],
  "external_resources": [...]
}
"""


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Process a transcript chunk")
    parser.add_argument("command", choices=["show", "save", "prompt"])
    parser.add_argument("--slug", type=str, help="Source slug (preferred)")
    parser.add_argument("--source-id", type=int, help="Source ID")
    parser.add_argument("--chunk-id", type=int, required=True)
    parser.add_argument("--result", type=str, help="JSON result to save (for 'save' command)")

    args = parser.parse_args()

    slug = args.slug
    source_id = args.source_id
    if not slug and not source_id:
        progress = get_progress()
        slug = progress.get('slug')
        source_id = progress.get('source_id')

    if args.command == "show":
        print_chunk_for_analysis(slug=slug, source_id=source_id, chunk_id=args.chunk_id)

    elif args.command == "prompt":
        print(EXTRACTION_PROMPT)
        print("\n--- CHUNK CONTENT ---\n")
        print_chunk_for_analysis(slug=slug, source_id=source_id, chunk_id=args.chunk_id)

    elif args.command == "save":
        if not args.result:
            print("ERROR: --result required for save command")
            sys.exit(1)
        result = json.loads(args.result)
        path = save_chunk_result(slug=slug, source_id=source_id, chunk_id=args.chunk_id, result=result)
        print(f"Saved to {path}")
