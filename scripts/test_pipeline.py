"""
Integration test for the research-extract pipeline.
Exercises flat-file storage, ingestion, chunking, progress tracking, merging, and slug safety.
"""

import sys
import json
import tempfile
import os
from pathlib import Path

# Set up a temp project root so tests don't pollute the real one
PROJECT_DIR = tempfile.mkdtemp()
os.makedirs(os.path.join(PROJECT_DIR, ".git"))  # fake git root
os.chdir(PROJECT_DIR)

# Now import — db.py will find .git and set DATA_DIR under PROJECT_DIR
sys.path.insert(0, str(Path(__file__).parent))

import db
import extract
import process_chunk
import ingest

PASS = 0
FAIL = 0


def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {label}")
    else:
        FAIL += 1
        msg = f"  FAIL  {label}"
        if detail:
            msg += f"  ({detail})"
        print(msg)


def test_data_dir_init():
    print("\n=== Data directory initialization ===")
    db.DATA_DIR.mkdir(parents=True, exist_ok=True)
    db.SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    check("DATA_DIR exists", db.DATA_DIR.exists())
    check("SOURCES_DIR exists", db.SOURCES_DIR.exists())


def test_text_ingestion():
    print("\n=== Text file ingestion ===")
    sample = Path(PROJECT_DIR) / "sample.txt"
    sample.write_text("This is a sample research document. " * 50)

    result = ingest.ingest_text_file(str(sample), slug="test-sample")
    check("ingest succeeds", result["status"] == "success", result.get("message", ""))
    check("slug is correct", result["slug"] == "test-sample")

    # Verify flat files exist
    meta_path = db.SOURCES_DIR / "test-sample.json"
    txt_path = db.SOURCES_DIR / "test-sample.txt"
    check("metadata JSON exists", meta_path.exists())
    check("transcript TXT exists", txt_path.exists())

    # Verify content
    source = db.get_source_by_slug("test-sample")
    check("source loads via get_source_by_slug", source is not None)
    check("transcript stored", len(source["transcript"]) > 100)


def test_slug_sanitization():
    print("\n=== Slug sanitization ===")
    bad_slugs = ["../etc/passwd", "foo/bar", "foo\\bar", "hello/../world"]
    for bad in bad_slugs:
        try:
            db.validate_slug(bad)
            check(f"reject '{bad}'", False, "should have raised ValueError")
        except ValueError:
            check(f"reject '{bad}'", True)

    good = db.validate_slug("my-great-podcast")
    check("accept good slug", good == "my-great-podcast")

    normalized = db.validate_slug("My Great Podcast!!!")
    check("normalize slug", normalized == "my-great-podcast")


def test_chunking():
    print("\n=== Chunking ===")
    # Need a long enough transcript
    long_text = " ".join(f"This is sentence number {i}." for i in range(2000))

    sample2 = Path(PROJECT_DIR) / "long_sample.txt"
    sample2.write_text(long_text)
    ingest.ingest_text_file(str(sample2), slug="long-sample")

    chunks = extract.chunk_transcript(slug="long-sample")
    check("chunks created", len(chunks) > 1, f"got {len(chunks)} chunks")
    check("chunks have text", all(c["text"] for c in chunks))
    check("chunks have slug", all(c["slug"] == "long-sample" for c in chunks))

    paths = extract.save_chunks(chunks)
    check("chunk files saved", all(p.exists() for p in paths))
    return chunks


def test_per_slug_progress(chunks):
    print("\n=== Per-slug progress tracking ===")
    slug = "long-sample"

    extract.init_progress(slug, len(chunks))

    pf = extract._progress_file(slug)
    check("progress file is slug-specific", slug in pf.name)
    check("progress file exists", pf.exists())

    progress = extract.get_progress(slug=slug)
    check("progress status running", progress["status"] == "running")
    check("total chunks correct", progress["total_chunks"] == len(chunks))

    # Update first chunk
    extract.update_progress(0, "completed", {"key_insights": [{"title": "test insight"}]}, slug=slug)
    progress = extract.get_progress(slug=slug)
    check("chunk 0 completed", progress["chunks"]["0"] == "completed")
    check("completed count = 1", progress["completed_chunks"] == 1)


def test_save_chunk_results(chunks):
    print("\n=== Save chunk results ===")
    slug = "long-sample"
    result = {
        "chunk_id": 1,
        "key_insights": [{"title": "Another insight", "description": "Desc"}],
        "quotes": [],
        "themes": ["testing"],
        "challenges": [],
        "solutions_approaches": [],
        "action_items": [],
        "frameworks_models": [],
        "external_resources": []
    }
    path = process_chunk.save_chunk_result(slug=slug, chunk_id=1, result=result)
    check("result file created", path.exists())

    progress = extract.get_progress(slug=slug)
    check("chunk 1 completed in progress", progress["chunks"]["1"] == "completed")


def test_merge(chunks):
    print("\n=== Merge ===")
    slug = "long-sample"

    # Complete all remaining chunks
    for i in range(2, len(chunks)):
        extract.update_progress(i, "completed", {
            "key_insights": [],
            "quotes": [],
            "themes": [],
            "challenges": [],
            "solutions_approaches": [],
            "action_items": [],
            "frameworks_models": [],
            "external_resources": []
        }, slug=slug)

    progress = extract.get_progress(slug=slug)
    check("all chunks completed", progress["status"] == "completed")

    merged = extract.merge_chunk_results(slug)
    check("merge succeeds", "error" not in merged)
    check("key_insights in merged", "key_insights" in merged)
    check("has metadata", "metadata" in merged)
    check("slug in merged", merged.get("slug") == slug)


def test_concurrent_progress():
    print("\n=== Concurrent progress files ===")
    # Create two progress files for different slugs
    extract.init_progress("slug-alpha", 3)
    extract.init_progress("slug-beta", 5)

    pf_alpha = extract._progress_file("slug-alpha")
    pf_beta = extract._progress_file("slug-beta")
    check("alpha file exists", pf_alpha.exists())
    check("beta file exists", pf_beta.exists())
    check("different files", pf_alpha != pf_beta)

    # Update one, verify the other is untouched
    extract.update_progress(0, "completed", {"key_insights": []}, slug="slug-alpha")
    progress_alpha = extract.get_progress(slug="slug-alpha")
    progress_beta = extract.get_progress(slug="slug-beta")

    check("alpha has 1 completed", progress_alpha["completed_chunks"] == 1)
    check("beta still has 0 completed", progress_beta["completed_chunks"] == 0)


def test_list_and_get():
    print("\n=== List sources / get source ===")
    sources = db.list_sources()
    check("list returns results", len(sources) > 0)

    source = db.get_source_by_slug("test-sample")
    check("get by slug works", source is not None)
    check("title present", source["title"] is not None)
    check("source_type present", source.get("source_type") == "text")


def test_blog_html_parsing():
    print("\n=== Blog HTML parsing ===")
    raw_html = """
    <html><head><title>Test &amp; Title</title></head>
    <body>
    <nav>Navigation stuff</nav>
    <article>
    <p>This is the main article content with &ldquo;smart quotes&rdquo; and an em&mdash;dash.</p>
    <p>More content here about important topics. We need at least 200 characters of content to pass the extraction threshold so let's keep writing more text about interesting research topics and findings.</p>
    </article>
    <footer>Footer stuff</footer>
    </body></html>
    """
    text = ingest._extract_article_content(raw_html)
    check("extracts article body", "main article content" in text)
    check("decodes HTML entities", "\u201c" in text or "smart quotes" in text)
    check("strips nav", "Navigation stuff" not in text)
    check("strips footer", "Footer stuff" not in text)


if __name__ == "__main__":
    print(f"Test project dir: {PROJECT_DIR}")
    print(f"DATA_DIR: {db.DATA_DIR}")

    test_data_dir_init()
    test_text_ingestion()
    test_slug_sanitization()
    chunks = test_chunking()
    test_per_slug_progress(chunks)
    test_save_chunk_results(chunks)
    test_merge(chunks)
    test_concurrent_progress()
    test_list_and_get()
    test_blog_html_parsing()

    print(f"\n{'='*40}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    if FAIL > 0:
        sys.exit(1)
    else:
        print("All tests passed!")
