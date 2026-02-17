"""
Ingest Module
Main entry point for ingesting content from various sources.
"""

import sys
import json
import re
import html
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))

from db import add_source, get_source_by_url, get_source, get_source_by_slug, validate_slug
from transcribe import transcribe_youtube, get_youtube_id, transcribe_audio_file


def _sanitize_slug(slug: Optional[str]) -> Optional[str]:
    """Sanitize a user-provided slug, returning None if not provided."""
    if slug is None:
        return None
    return validate_slug(slug)


def detect_source_type(input_str: str) -> tuple[str, str]:
    """
    Detect the type of source from input.
    Returns: (source_type, normalized_input)
    """
    path = Path(input_str)
    if path.exists():
        suffix = path.suffix.lower()
        if suffix == '.pdf':
            return 'pdf', str(path.absolute())
        elif suffix in ['.txt', '.md', '.markdown']:
            return 'text', str(path.absolute())
        elif suffix in ['.mp3', '.wav', '.m4a']:
            return 'audio', str(path.absolute())
        else:
            return 'file', str(path.absolute())

    if input_str.startswith(('http://', 'https://', 'www.')):
        if not input_str.startswith('http'):
            input_str = 'https://' + input_str

        parsed = urlparse(input_str)
        domain = parsed.netloc.lower()

        if 'youtube.com' in domain or 'youtu.be' in domain:
            return 'youtube', input_str
        else:
            return 'blog', input_str

    return 'unknown', input_str


def _extract_article_content(raw_html: str) -> str:
    """Extract article body from HTML, preferring semantic containers."""
    # Try semantic containers first: <article>, <main>, large role="main"
    for tag in ['article', 'main']:
        pattern = rf'<{tag}[^>]*>(.*?)</{tag}>'
        match = re.search(pattern, raw_html, re.DOTALL | re.IGNORECASE)
        if match and len(match.group(1)) > 200:
            raw_html = match.group(1)
            break

    # Strip scripts, styles, nav, header, footer
    for tag in ['script', 'style', 'nav', 'header', 'footer', 'aside']:
        raw_html = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', '', raw_html, flags=re.DOTALL | re.IGNORECASE)

    # Strip all remaining tags
    text = re.sub(r'<[^>]+>', ' ', raw_html)
    # Decode all HTML entities
    text = html.unescape(text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def ingest_youtube(url: str, slug: Optional[str] = None) -> dict:
    """Ingest a YouTube video."""
    slug = _sanitize_slug(slug)

    existing = get_source_by_url(url)
    if existing:
        return {
            "status": "exists",
            "source_id": existing["id"],
            "slug": existing.get("slug"),
            "title": existing["title"],
            "message": "Already ingested"
        }

    if slug:
        existing = get_source_by_slug(slug)
        if existing:
            return {
                "status": "error",
                "message": f"Slug '{slug}' already in use"
            }

    transcript, metadata = transcribe_youtube(url)

    if not transcript:
        return {
            "status": "error",
            "message": "Failed to transcribe video"
        }

    source_id, final_slug = add_source(
        source_type="youtube",
        url=url,
        title=metadata.get("title"),
        transcript=transcript,
        metadata=metadata,
        slug=slug
    )

    return {
        "status": "success",
        "source_id": source_id,
        "slug": final_slug,
        "title": metadata.get("title"),
        "duration": metadata.get("duration"),
        "method": metadata.get("transcription_method"),
        "transcript_length": len(transcript)
    }


def ingest_blog(url: str, slug: Optional[str] = None) -> dict:
    """Ingest a blog/web article."""
    slug = _sanitize_slug(slug)

    existing = get_source_by_url(url)
    if existing:
        return {
            "status": "exists",
            "source_id": existing["id"],
            "slug": existing.get("slug"),
            "title": existing["title"],
            "message": "Already ingested"
        }

    if slug:
        existing = get_source_by_slug(slug)
        if existing:
            return {
                "status": "error",
                "message": f"Slug '{slug}' already in use"
            }

    try:
        result = subprocess.run(
            ["curl", "-sL", "-A", "Mozilla/5.0", url],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return {"status": "error", "message": "Failed to fetch URL"}

        raw = result.stdout

        title_match = re.search(r'<title[^>]*>([^<]+)</title>', raw, re.IGNORECASE)
        title = html.unescape(title_match.group(1).strip()) if title_match else "Unknown"

        text = _extract_article_content(raw)

        if len(text) < 100:
            return {"status": "error", "message": "Could not extract meaningful content"}

        source_id, final_slug = add_source(
            source_type="blog",
            url=url,
            title=title,
            transcript=text,
            metadata={"url": url},
            slug=slug
        )

        return {
            "status": "success",
            "source_id": source_id,
            "slug": final_slug,
            "title": title,
            "content_length": len(text)
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def ingest_text_file(filepath: str, slug: Optional[str] = None) -> dict:
    """Ingest a local text file."""
    slug = _sanitize_slug(slug)
    path = Path(filepath)

    if not path.exists():
        return {"status": "error", "message": "File not found"}

    if slug:
        existing = get_source_by_slug(slug)
        if existing:
            return {
                "status": "error",
                "message": f"Slug '{slug}' already in use"
            }

    try:
        content = path.read_text()
        title = path.stem

        source_id, final_slug = add_source(
            source_type="text",
            filepath=str(path.absolute()),
            title=title,
            transcript=content,
            metadata={"filename": path.name, "size": path.stat().st_size},
            slug=slug or path.stem.lower().replace(" ", "-")
        )

        return {
            "status": "success",
            "source_id": source_id,
            "slug": final_slug,
            "title": title,
            "content_length": len(content)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def ingest_pdf(filepath: str, slug: Optional[str] = None) -> dict:
    """Ingest a PDF file (requires pdftotext)."""
    slug = _sanitize_slug(slug)
    path = Path(filepath)

    if not path.exists():
        return {"status": "error", "message": "File not found"}

    if slug:
        existing = get_source_by_slug(slug)
        if existing:
            return {
                "status": "error",
                "message": f"Slug '{slug}' already in use"
            }

    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            return {
                "status": "error",
                "message": "pdftotext not installed. Install with: brew install poppler (macOS) or apt install poppler-utils (Linux)"
            }

        content = result.stdout
        title = path.stem

        source_id, final_slug = add_source(
            source_type="pdf",
            filepath=str(path.absolute()),
            title=title,
            transcript=content,
            metadata={"filename": path.name, "size": path.stat().st_size},
            slug=slug or path.stem.lower().replace(" ", "-")
        )

        return {
            "status": "success",
            "source_id": source_id,
            "slug": final_slug,
            "title": title,
            "content_length": len(content)
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "message": "pdftotext not installed. Install with: brew install poppler (macOS) or apt install poppler-utils (Linux)"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def ingest_audio(filepath: str, slug: Optional[str] = None, model: str = "base") -> dict:
    """Ingest an audio file (mp3, wav, m4a, etc.) using Whisper transcription."""
    slug = _sanitize_slug(slug)
    path = Path(filepath)

    if not path.exists():
        return {"status": "error", "message": "File not found"}

    if slug:
        existing = get_source_by_slug(slug)
        if existing:
            return {
                "status": "error",
                "message": f"Slug '{slug}' already in use"
            }

    try:
        print(f"Transcribing audio file: {path.name}")
        transcript = transcribe_audio_file(str(path.absolute()), model=model)

        if not transcript:
            return {"status": "error", "message": "Failed to transcribe audio"}

        title = path.stem
        final_slug = slug or path.stem.lower().replace(" ", "-").replace("_", "-")

        source_id, final_slug = add_source(
            source_type="audio",
            filepath=str(path.absolute()),
            title=title,
            transcript=transcript,
            metadata={
                "filename": path.name,
                "size": path.stat().st_size,
                "transcription_method": "whisper",
                "whisper_model": model
            },
            slug=final_slug
        )

        return {
            "status": "success",
            "source_id": source_id,
            "slug": final_slug,
            "title": title,
            "transcript_length": len(transcript),
            "method": "whisper"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def ingest(input_str: str, slug: Optional[str] = None) -> dict:
    """Main ingest function - auto-detects source type and ingests."""
    source_type, normalized = detect_source_type(input_str)

    if source_type == 'youtube':
        return ingest_youtube(normalized, slug)
    elif source_type == 'blog':
        return ingest_blog(normalized, slug)
    elif source_type == 'text':
        return ingest_text_file(normalized, slug)
    elif source_type == 'pdf':
        return ingest_pdf(normalized, slug)
    elif source_type == 'audio':
        return ingest_audio(normalized, slug)
    elif source_type == 'file':
        return ingest_text_file(normalized, slug)
    else:
        return {"status": "error", "message": f"Unknown source type: {input_str}"}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest content from various sources")
    parser.add_argument("input", help="URL or filepath to ingest")
    parser.add_argument("--slug", help="Custom slug name for this source")

    if len(sys.argv) > 1:
        args = parser.parse_args()
        print(f"Ingesting: {args.input}")
        if args.slug:
            print(f"Using slug: {args.slug}")
        result = ingest(args.input, args.slug)
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()
        print("\nSupported:")
        print("  - YouTube URLs")
        print("  - Blog/article URLs")
        print("  - Text files (.txt, .md)")
        print("  - PDF files (.pdf)")
        print("  - Audio files (.mp3, .wav, .m4a)")
