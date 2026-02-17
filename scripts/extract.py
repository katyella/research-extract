"""
Extraction Module
Chunks transcripts and manages extraction progress.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from db import get_source, get_source_by_slug, add_extraction, DATA_DIR

CHUNKS_DIR = DATA_DIR / "chunks"
EXPORTS_DIR = DATA_DIR / "exports"


def _progress_file(slug: str) -> Path:
    """Return the progress file path for a given slug."""
    return DATA_DIR / f"extraction_progress_{slug}.json"


def chunk_transcript(slug: str = None, source_id: int = None, chunk_size: int = 15000) -> list[dict]:
    """
    Split a transcript into chunks for parallel processing.
    Returns list of chunk dicts with metadata.
    Accepts either slug or source_id.
    """
    if slug:
        source = get_source_by_slug(slug)
    elif source_id:
        source = get_source(source_id)
    else:
        return []

    if not source:
        return []

    transcript = source['transcript']
    title = source['title']
    source_slug = source.get('slug') or f"source_{source['id']}"
    chunks = []

    text = transcript
    chunk_num = 0
    start_char = 0

    while text:
        if len(text) <= chunk_size:
            chunks.append({
                "chunk_id": chunk_num,
                "slug": source_slug,
                "source_id": source['id'],
                "title": title,
                "start_char": start_char,
                "text": text.strip(),
                "char_count": len(text)
            })
            break

        chunk_text = text[:chunk_size]

        best_break = chunk_size
        for end_char in ['. ', '! ', '? ', '." ', '.) ']:
            pos = chunk_text.rfind(end_char)
            if pos > chunk_size * 0.7:
                best_break = pos + len(end_char)
                break

        chunk_text = text[:best_break]
        chunks.append({
            "chunk_id": chunk_num,
            "slug": source_slug,
            "source_id": source['id'],
            "title": title,
            "start_char": start_char,
            "text": chunk_text.strip(),
            "char_count": len(chunk_text)
        })

        start_char += best_break
        text = text[best_break:]
        chunk_num += 1

    return chunks


def save_chunks(chunks: list[dict]) -> list[Path]:
    """Save chunks to individual files for parallel processing."""
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    paths = []
    for chunk in chunks:
        slug = chunk.get('slug', f"source_{chunk['source_id']}")
        chunk_path = CHUNKS_DIR / f"{slug}_chunk_{chunk['chunk_id']}.json"
        with open(chunk_path, 'w') as f:
            json.dump(chunk, f, indent=2)
        paths.append(chunk_path)

    return paths


def init_progress(slug: str, source_id: int, total_chunks: int) -> dict:
    """Initialize progress tracking for an extraction."""
    progress = {
        "slug": slug,
        "source_id": source_id,
        "total_chunks": total_chunks,
        "completed_chunks": 0,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "chunks": {str(i): "pending" for i in range(total_chunks)},
        "results": {}
    }
    pf = _progress_file(slug)
    pf.parent.mkdir(parents=True, exist_ok=True)
    with open(pf, 'w') as f:
        json.dump(progress, f, indent=2)
    return progress


def update_progress(chunk_id: int, status: str, result: dict = None, slug: str = None):
    """Update progress for a specific chunk."""
    pf = _progress_file(slug) if slug else None
    if not pf or not pf.exists():
        return

    with open(pf, 'r') as f:
        progress = json.load(f)

    progress['chunks'][str(chunk_id)] = status
    if status == "completed":
        progress['completed_chunks'] += 1
        if result:
            progress['results'][str(chunk_id)] = result

    if progress['completed_chunks'] >= progress['total_chunks']:
        progress['status'] = "completed"
        progress['completed_at'] = datetime.now().isoformat()

    with open(pf, 'w') as f:
        json.dump(progress, f, indent=2)


def get_progress(slug: str = None) -> dict:
    """Get current extraction progress for a slug."""
    pf = _progress_file(slug) if slug else None
    if not pf or not pf.exists():
        return {"status": "no_extraction"}

    with open(pf, 'r') as f:
        progress = json.load(f)

    if progress['total_chunks'] > 0:
        progress['percent'] = int(100 * progress['completed_chunks'] / progress['total_chunks'])
    else:
        progress['percent'] = 0

    return progress


def print_progress_bar(slug: str = None):
    """Print a simple progress bar to stdout."""
    progress = get_progress(slug=slug)
    if progress['status'] == "no_extraction":
        print("No extraction in progress")
        return

    completed = progress['completed_chunks']
    total = progress['total_chunks']
    percent = progress['percent']

    bar_width = 30
    filled = int(bar_width * completed / total) if total > 0 else 0
    bar = "#" * filled + "-" * (bar_width - filled)

    print(f"\r[{bar}] {percent}% ({completed}/{total} chunks)", end="", flush=True)

    if progress['status'] == "completed":
        print(" Done!")


def merge_chunk_results(source_id: int, slug: str = None) -> dict:
    """Merge results from all chunks into a single extraction."""
    progress = get_progress(slug=slug)
    if progress['status'] != "completed":
        return {"error": "Extraction not complete"}

    all_key_insights = []
    all_quotes = []
    all_themes = []
    all_challenges = []
    all_solutions_approaches = []
    all_action_items = []
    all_frameworks_models = []
    all_external_resources = []

    for chunk_id, result in progress['results'].items():
        if isinstance(result, dict):
            all_key_insights.extend(result.get('key_insights', []))
            all_quotes.extend(result.get('quotes', []))
            all_themes.extend(result.get('themes', []))
            all_challenges.extend(result.get('challenges', []))
            all_solutions_approaches.extend(result.get('solutions_approaches', []))
            all_action_items.extend(result.get('action_items', []))
            all_frameworks_models.extend(result.get('frameworks_models', []))
            all_external_resources.extend(result.get('external_resources', []))

    merged = {
        "source_id": source_id,
        "key_insights": _dedupe_by_content(all_key_insights),
        "quotes": _dedupe_by_content(all_quotes),
        "themes": _dedupe_by_content(all_themes),
        "challenges": _dedupe_by_content(all_challenges),
        "solutions_approaches": _dedupe_by_content(all_solutions_approaches),
        "action_items": _dedupe_by_content(all_action_items),
        "frameworks_models": _dedupe_by_content(all_frameworks_models),
        "external_resources": _dedupe_resources(all_external_resources),
        "metadata": {
            "extraction_date": datetime.now().isoformat(),
            "total_chunks": progress['total_chunks']
        }
    }

    return merged


def _dedupe_by_content(items: list) -> list:
    """Remove duplicates based on main content field."""
    seen = set()
    unique = []
    for item in items:
        if isinstance(item, str):
            content = item
        else:
            content = (
                item.get('title') or
                item.get('quote') or
                item.get('action') or
                item.get('name') or
                item.get('theme') or
                str(item)
            )
        if content not in seen:
            seen.add(content)
            unique.append(item)
    return unique


def _dedupe_resources(resources: list) -> list:
    """Deduplicate external resources by name, grouping by type."""
    if not resources:
        return []

    seen = {}
    for res in resources:
        if not isinstance(res, dict):
            continue
        res_type = res.get('type', 'other')
        name = res.get('name', '')
        if not name:
            continue

        key = (res_type, name.lower().strip())
        if key not in seen:
            seen[key] = res
        else:
            existing = seen[key]
            if len(str(res)) > len(str(existing)):
                seen[key] = res

    result = sorted(seen.values(), key=lambda x: (x.get('type', 'z'), x.get('name', '').lower()))
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extraction utilities")
    parser.add_argument("command", choices=["chunk", "progress", "merge"])
    parser.add_argument("--slug", help="Source slug (preferred)")
    parser.add_argument("--source-id", type=int, help="Source ID")
    parser.add_argument("--watch", action="store_true", help="Watch progress continuously")

    args = parser.parse_args()

    if args.command == "chunk":
        if not args.slug and not args.source_id:
            print("--slug or --source-id required")
            sys.exit(1)
        chunks = chunk_transcript(slug=args.slug, source_id=args.source_id)
        if not chunks:
            print("No source found or empty transcript")
            sys.exit(1)
        paths = save_chunks(chunks)
        slug = chunks[0].get('slug', f"source_{chunks[0]['source_id']}")
        source_id = chunks[0]['source_id']
        print(f"Created {len(chunks)} chunks for '{slug}':")
        for i, chunk in enumerate(chunks):
            print(f"  Chunk {i}: {chunk['char_count']} chars")
        init_progress(slug, source_id, len(chunks))
        print(f"\nChunks saved to {CHUNKS_DIR}")

    elif args.command == "progress":
        if not args.slug:
            print("--slug required for progress tracking")
            sys.exit(1)
        if args.watch:
            import time
            while True:
                print_progress_bar(slug=args.slug)
                progress = get_progress(slug=args.slug)
                if progress.get('status') == "completed":
                    break
                time.sleep(1)
        else:
            progress = get_progress(slug=args.slug)
            print(json.dumps(progress, indent=2))

    elif args.command == "merge":
        if not args.slug:
            print("--slug required for merge")
            sys.exit(1)
        progress = get_progress(slug=args.slug)
        source_id = progress.get('source_id')
        slug = progress.get('slug')
        if not source_id:
            print("No extraction in progress for this slug")
            sys.exit(1)
        merged = merge_chunk_results(source_id, slug=slug)
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = EXPORTS_DIR / f"{slug}_merged.json"
        with open(output_path, 'w') as f:
            json.dump(merged, f, indent=2)
        print(f"Merged results saved to {output_path}")
        print(json.dumps(merged, indent=2))
