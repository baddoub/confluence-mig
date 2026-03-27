"""Fetch all pages from a legacy Confluence space into raw/."""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

from scripts.confluence_client import ConfluenceClient

RAW_DIR = Path("raw")


def slugify(title: str) -> str:
    """Convert a page title to a filesystem-safe slug."""
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug.strip("-")[:80]


def load_space_config() -> dict:
    with open("config/spaces.yaml") as f:
        return yaml.safe_load(f)


def fetch_page_with_body(client: ConfluenceClient, page_id: str) -> dict:
    """Fetch a page including its storage-format body."""
    return client.get_page_by_id(page_id, body_format="storage")


def save_page(page: dict, labels: list[str]) -> Path:
    """Save a page's HTML body and metadata to raw/."""
    page_id = page["id"]
    title = page.get("title", "untitled")
    slug = slugify(title)
    prefix = f"{page_id}_{slug}"

    body = page.get("body", {}).get("storage", {}).get("value", "")
    html_path = RAW_DIR / f"{prefix}.html"
    html_path.write_text(body, encoding="utf-8")

    meta = {
        "id": page_id,
        "title": title,
        "slug": slug,
        "status": page.get("status"),
        "parentId": page.get("parentId"),
        "parentType": page.get("parentType"),
        "labels": labels,
        "createdAt": page.get("createdAt"),
        "version": page.get("version", {}).get("number"),
        "authorId": page.get("authorId"),
    }
    meta_path = RAW_DIR / f"{prefix}.meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return html_path


def should_skip(page_id: str, slug: str) -> bool:
    """Check if a page was already fetched (for incremental fetches)."""
    prefix = f"{page_id}_{slug}"
    return (RAW_DIR / f"{prefix}.html").exists() and (RAW_DIR / f"{prefix}.meta.json").exists()


def main():
    parser = argparse.ArgumentParser(description="Fetch legacy Confluence space")
    parser.add_argument("--dry-run", action="store_true", help="List pages without downloading")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if already downloaded")
    args = parser.parse_args()

    config = load_space_config()
    legacy_key = config["legacy"]["space_key"]

    client = ConfluenceClient()

    # Resolve space key to space ID
    space = client.get_space_by_key(legacy_key)
    space_id = str(space["id"])
    print(f"Space: {space['name']} (key={legacy_key}, id={space_id})")

    # Fetch page list
    print("Fetching page list...")
    pages = client.get_pages_in_space(space_id)
    print(f"Found {len(pages)} pages in space")

    if args.dry_run:
        for p in pages:
            print(f"  [{p['id']}] {p['title']}")
        return

    RAW_DIR.mkdir(exist_ok=True)
    fetched = 0
    skipped = 0
    errors = []

    for page_summary in pages:
        page_id = page_summary["id"]
        title = page_summary.get("title", "untitled")
        slug = slugify(title)

        if not args.force and should_skip(page_id, slug):
            skipped += 1
            continue

        try:
            page = fetch_page_with_body(client, page_id)
            labels = client.get_page_labels(page_id)
            save_page(page, labels)
            fetched += 1
            print(f"  Fetched: {title}")
        except Exception as e:
            errors.append({"page_id": page_id, "title": title, "error": str(e)})
            print(f"  ERROR: {title} - {e}", file=sys.stderr)

    print(f"\nSummary: {fetched} fetched, {skipped} skipped, {len(errors)} errors")
    if errors:
        print("Errors:")
        for err in errors:
            print(f"  [{err['page_id']}] {err['title']}: {err['error']}")


if __name__ == "__main__":
    main()
