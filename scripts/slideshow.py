"""
Slideshow Generator
Converts consolidated extraction JSON into a presentation PDF.
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from db import DATA_DIR

EXPORTS_DIR = DATA_DIR / "exports"
SLIDES_DIR = DATA_DIR / "slides"
TEMPLATE_DIR = Path(__file__).parent.parent / "assets" / "templates"


def load_consolidated(slug: str) -> dict:
    """Load the consolidated JSON for a source."""
    path = EXPORTS_DIR / f"{slug}_consolidated.json"
    if not path.exists():
        print(f"ERROR: No consolidated file found at {path}")
        print(f"Run the full extraction and consolidation first.")
        sys.exit(1)
    with open(path, 'r') as f:
        return json.load(f)


def build_slides(data: dict) -> list[dict]:
    """Convert consolidated data into a list of slide dicts."""
    slides = []

    # 1. Title slide
    slides.append({
        "type": "title",
        "title": data.get("source", "Research Extract"),
        "speakers": data.get("speakers", []),
        "date": data.get("metadata", {}).get("extraction_date", ""),
        "url": data.get("url", ""),
    })

    # 2. Themes overview
    themes = data.get("themes", [])
    if themes:
        # Handle both string themes and dict themes with frequency
        theme_items = []
        for t in themes:
            if isinstance(t, str):
                theme_items.append({"theme": t})
            elif isinstance(t, dict):
                theme_items.append(t)
        slides.append({
            "type": "themes",
            "title": "Key Themes",
            "items": theme_items[:12],
        })

    # 3. Key insights (max 3 slides, 2 per slide)
    insights = data.get("key_insights", [])
    for i in range(0, min(len(insights), 6), 2):
        batch = insights[i:i+2]
        slides.append({
            "type": "insights",
            "title": "Key Insights",
            "items": batch,
        })

    # 4. Top quotes (max 3)
    quotes = data.get("top_quotes", [])
    for q in quotes[:3]:
        slides.append({
            "type": "quote",
            "quote": q.get("quote", ""),
            "speaker": q.get("speaker", ""),
            "context": q.get("context", ""),
        })

    # 5. Challenges & Solutions
    challenges = data.get("challenges", [])
    solutions = data.get("solutions_approaches", data.get("solutions", []))
    if challenges or solutions:
        slides.append({
            "type": "challenges_solutions",
            "title": "Challenges & Solutions",
            "challenges": challenges[:4],
            "solutions": solutions[:4],
        })

    # 6. Frameworks
    frameworks = data.get("frameworks_models", [])
    if frameworks:
        slides.append({
            "type": "frameworks",
            "title": "Frameworks & Models",
            "items": frameworks[:6],
        })

    # 7. Action items
    actions = data.get("action_items", [])
    if actions:
        slides.append({
            "type": "actions",
            "title": "Action Items",
            "items": actions[:8],
        })

    # 8. External resources
    resources = data.get("external_resources", {})
    # Handle both list and dict formats
    if isinstance(resources, list):
        if resources:
            slides.append({
                "type": "resources",
                "title": "Resources Mentioned",
                "items": resources[:12],
            })
    elif isinstance(resources, dict):
        all_resources = []
        for category, items in resources.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        item.setdefault("type", category.rstrip("s"))
                        all_resources.append(item)
        if all_resources:
            slides.append({
                "type": "resources",
                "title": "Resources Mentioned",
                "items": all_resources[:12],
            })

    return slides


def render_slideshow(slides: list[dict]) -> str:
    """Render slides to HTML using Jinja2 template."""
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError:
        print("ERROR: Jinja2 not installed. Run: bash scripts/setup.sh")
        sys.exit(1)

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("slideshow.html")
    return template.render(slides=slides)


def generate_slideshow(slug: str) -> Path:
    """Generate a PDF slideshow from consolidated data."""
    try:
        from weasyprint import HTML
    except ImportError:
        print("ERROR: WeasyPrint not installed. Run: bash scripts/setup.sh")
        sys.exit(1)

    data = load_consolidated(slug)
    slides = build_slides(data)
    html_content = render_slideshow(slides)

    SLIDES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = SLIDES_DIR / f"{slug}-slides.pdf"

    css_path = TEMPLATE_DIR / "styles" / "slideshow.css"
    HTML(string=html_content).write_pdf(
        str(output_path),
        stylesheets=[str(css_path)] if css_path.exists() else []
    )

    print(f"Slideshow generated: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate slideshow PDFs from extractions")
    parser.add_argument("command", choices=["generate", "preview"])
    parser.add_argument("--slug", required=True, help="Source slug")

    args = parser.parse_args()

    if args.command == "generate":
        generate_slideshow(args.slug)
    elif args.command == "preview":
        data = load_consolidated(args.slug)
        slides = build_slides(data)
        html = render_slideshow(slides)
        preview_path = SLIDES_DIR / f"{args.slug}-preview.html"
        SLIDES_DIR.mkdir(parents=True, exist_ok=True)
        preview_path.write_text(html)
        print(f"HTML preview saved: {preview_path}")
