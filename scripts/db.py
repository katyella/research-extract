"""
Research Extract Data Module
Flat-file operations for storing sources, transcripts, and metadata.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


def _get_project_root() -> Path:
    """Walk up from cwd to find project root (has .git/ or .claude/)."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".git").exists() or (parent / ".claude").exists():
            return parent
    return cwd


DATA_DIR = _get_project_root() / ".research-extract"
SOURCES_DIR = DATA_DIR / "sources"


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text[:50]


def validate_slug(slug: str) -> str:
    """Validate and sanitize a slug. Raises ValueError for unsafe slugs."""
    if not slug:
        raise ValueError("Slug cannot be empty")
    if '..' in slug or '/' in slug or '\\' in slug:
        raise ValueError(f"Slug contains unsafe characters: {slug!r}")
    return slugify(slug)


def add_source(
    source_type: str,
    transcript: str,
    url: Optional[str] = None,
    filepath: Optional[str] = None,
    title: Optional[str] = None,
    metadata: Optional[dict] = None,
    slug: Optional[str] = None
) -> tuple[str]:
    """Add a new source. Writes {slug}.json metadata and {slug}.txt transcript. Returns (slug,)."""
    if not slug and title:
        slug = slugify(title)
    elif not slug:
        slug = f"source-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    meta = {
        "slug": slug,
        "url": url,
        "filepath": filepath,
        "source_type": source_type,
        "title": title,
        "metadata": metadata or {},
        "created_at": datetime.now().isoformat(),
        "transcript_file": f"{slug}.txt",
    }

    meta_path = SOURCES_DIR / f"{slug}.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    txt_path = SOURCES_DIR / f"{slug}.txt"
    txt_path.write_text(transcript)

    return (slug,)


def get_source_by_slug(slug: str) -> Optional[dict]:
    """Get a source by slug. Reads {slug}.json and loads transcript from {slug}.txt."""
    meta_path = SOURCES_DIR / f"{slug}.json"
    if not meta_path.exists():
        return None

    with open(meta_path, "r") as f:
        source = json.load(f)

    txt_path = SOURCES_DIR / f"{slug}.txt"
    if txt_path.exists():
        source["transcript"] = txt_path.read_text()
    else:
        source["transcript"] = ""

    return source


def get_source_by_url(url: str) -> Optional[dict]:
    """Get a source by URL (to avoid re-ingesting). Scans sources/*.json."""
    if not SOURCES_DIR.exists():
        return None

    for meta_path in SOURCES_DIR.glob("*.json"):
        with open(meta_path, "r") as f:
            source = json.load(f)
        if source.get("url") == url:
            return source

    return None


def list_sources(source_type: Optional[str] = None, limit: int = 50) -> list[dict]:
    """List sources, optionally filtered by type."""
    if not SOURCES_DIR.exists():
        return []

    sources = []
    for meta_path in sorted(SOURCES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        with open(meta_path, "r") as f:
            source = json.load(f)
        if source_type and source.get("source_type") != source_type:
            continue
        sources.append(source)
        if len(sources) >= limit:
            break

    return sources


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Data directory initialized at {DATA_DIR}")
    print(f"Sources directory: {SOURCES_DIR}")
