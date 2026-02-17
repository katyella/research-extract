"""
Research Extract Database Module
SQLite operations for storing sources, transcripts, and extractions.
"""

import sqlite3
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
DB_PATH = DATA_DIR / "research.db"


def get_connection() -> sqlite3.Connection:
    """Get a database connection, creating tables if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _init_tables(conn)
    return conn


def _init_tables(conn: sqlite3.Connection):
    """Initialize database tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT,
            url TEXT,
            filepath TEXT,
            source_type TEXT NOT NULL,
            title TEXT,
            transcript TEXT,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS extractions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            lens TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES sources(id)
        );

        CREATE INDEX IF NOT EXISTS idx_sources_url ON sources(url);
        CREATE INDEX IF NOT EXISTS idx_sources_slug ON sources(slug);
        CREATE INDEX IF NOT EXISTS idx_sources_type ON sources(source_type);
        CREATE INDEX IF NOT EXISTS idx_extractions_source ON extractions(source_id);
        CREATE INDEX IF NOT EXISTS idx_extractions_lens ON extractions(lens);
    """)
    conn.commit()


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
) -> tuple[int, str]:
    """Add a new source to the database. Returns (source_id, slug)."""
    if not slug and title:
        slug = slugify(title)
    elif not slug:
        slug = f"source-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO sources (slug, url, filepath, source_type, title, transcript, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (slug, url, filepath, source_type, title, transcript, json.dumps(metadata or {}))
        )
        conn.commit()
        source_id = cursor.lastrowid
        return source_id, slug
    finally:
        conn.close()


def get_source(source_id: int) -> Optional[dict]:
    """Get a source by ID."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def get_source_by_url(url: str) -> Optional[dict]:
    """Get a source by URL (to avoid re-ingesting)."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM sources WHERE url = ?", (url,)).fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def get_source_by_slug(slug: str) -> Optional[dict]:
    """Get a source by slug."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM sources WHERE slug = ?", (slug,)).fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def list_sources(source_type: Optional[str] = None, limit: int = 50) -> list[dict]:
    """List sources, optionally filtered by type."""
    conn = get_connection()
    try:
        if source_type:
            rows = conn.execute(
                "SELECT id, slug, url, filepath, source_type, title, created_at FROM sources WHERE source_type = ? ORDER BY created_at DESC LIMIT ?",
                (source_type, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, slug, url, filepath, source_type, title, created_at FROM sources ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def add_extraction(source_id: int, lens: str, content: dict) -> int:
    """Add an extraction for a source. Returns the extraction ID."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO extractions (source_id, lens, content)
            VALUES (?, ?, ?)
            """,
            (source_id, lens, json.dumps(content))
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_extractions(source_id: int) -> list[dict]:
    """Get all extractions for a source."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM extractions WHERE source_id = ? ORDER BY created_at DESC",
            (source_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def search_extractions(query: str, lens: Optional[str] = None) -> list[dict]:
    """Search extractions by content (simple LIKE search)."""
    conn = get_connection()
    try:
        if lens:
            rows = conn.execute(
                """
                SELECT e.*, s.title, s.url, s.source_type
                FROM extractions e
                JOIN sources s ON e.source_id = s.id
                WHERE e.content LIKE ? AND e.lens = ?
                ORDER BY e.created_at DESC
                """,
                (f"%{query}%", lens)
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT e.*, s.title, s.url, s.source_type
                FROM extractions e
                JOIN sources s ON e.source_id = s.id
                WHERE e.content LIKE ?
                ORDER BY e.created_at DESC
                """,
                (f"%{query}%",)
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_all_by_lens(lens: str) -> list[dict]:
    """Get all extractions for a specific lens."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT e.*, s.title, s.url, s.source_type
            FROM extractions e
            JOIN sources s ON e.source_id = s.id
            WHERE e.lens = ?
            ORDER BY e.created_at DESC
            """,
            (lens,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    conn = get_connection()
    print(f"Database initialized at {DB_PATH}")
    print("Tables created successfully")
    conn.close()
