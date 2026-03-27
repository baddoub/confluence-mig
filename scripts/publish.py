"""Publish markdown docs from docs/ to the new Confluence space."""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from scripts.confluence_client import ConfluenceClient

DOCS_DIR = Path("docs")


def load_space_config() -> dict:
    with open("config/spaces.yaml") as f:
        return yaml.safe_load(f)


def parse_frontmatter(filepath: Path) -> tuple[dict, str]:
    """Parse YAML frontmatter and body from a markdown file."""
    text = filepath.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2].strip()
    return meta, body


def update_frontmatter(filepath: Path, updates: dict):
    """Update specific frontmatter fields in a file."""
    meta, body = parse_frontmatter(filepath)
    meta.update(updates)

    frontmatter = yaml.dump(meta, default_flow_style=False, sort_keys=False).strip()
    filepath.write_text(f"---\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8")


def markdown_to_confluence_storage(markdown_body: str) -> str:
    """Convert markdown body to Confluence storage format.

    Uses md2cf for conversion. Falls back to basic HTML wrapping.
    """
    try:
        from md2cf.confluence_renderer import ConfluenceRenderer
        import mistune

        renderer = ConfluenceRenderer()
        md_parser = mistune.create_markdown(renderer=renderer)
        return md_parser(markdown_body)
    except ImportError:
        # Fallback: wrap in basic HTML (lossy but functional)
        from markdown import markdown

        return markdown(markdown_body, extensions=["tables", "fenced_code"])


def find_publishable_docs() -> list[Path]:
    """Find all docs with status: published or review."""
    docs = []
    for md_file in DOCS_DIR.rglob("*.md"):
        meta, _ = parse_frontmatter(md_file)
        if meta.get("status") in ("published", "review"):
            docs.append(md_file)
    return sorted(docs)


def resolve_parent_page(
    client: ConfluenceClient,
    space_id: str,
    doc_path: Path,
    hierarchy: dict,
    parent_cache: dict,
) -> str | None:
    """Find or create the parent page for a doc based on its directory."""
    # Map doc directory to hierarchy section
    relative = doc_path.relative_to(DOCS_DIR)
    section = relative.parts[0] if len(relative.parts) > 1 else None

    if not section or section not in hierarchy:
        return None

    parent_title = hierarchy[section]

    if parent_title in parent_cache:
        return parent_cache[parent_title]

    # Search for existing parent page
    results = client.search_pages(
        f'space.key="{space_id}" AND title="{parent_title}" AND type=page'
    )
    if results:
        parent_id = results[0]["id"]
        parent_cache[parent_title] = parent_id
        return parent_id

    # Create parent page if it doesn't exist
    page = client.create_page(
        space_id=space_id,
        title=parent_title,
        body=f"<p>Documentation section: {parent_title}</p>",
    )
    parent_id = page["id"]
    parent_cache[parent_title] = parent_id
    return parent_id


def main():
    parser = argparse.ArgumentParser(description="Publish docs to Confluence")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be published")
    args = parser.parse_args()

    config = load_space_config()
    new_key = config["new"]["space_key"]
    hierarchy = config["new"].get("hierarchy", {})

    client = ConfluenceClient()
    space = client.get_space_by_key(new_key)
    space_id = str(space["id"])
    print(f"Publishing to: {space['name']} (key={new_key})")

    docs = find_publishable_docs()
    if not docs:
        print("No docs with status 'published' or 'review' found.")
        return

    print(f"Found {len(docs)} docs to publish")

    if args.dry_run:
        for doc in docs:
            meta, _ = parse_frontmatter(doc)
            action = "UPDATE" if meta.get("confluence_page_id") else "CREATE"
            print(f"  [{action}] {meta.get('title', doc.stem)} ({doc})")
        return

    parent_cache: dict[str, str] = {}
    created = 0
    updated = 0
    errors = []

    for doc_path in docs:
        meta, body = parse_frontmatter(doc_path)
        title = meta.get("title", doc_path.stem)
        page_id = meta.get("confluence_page_id")

        try:
            storage_body = markdown_to_confluence_storage(body)
            parent_id = resolve_parent_page(
                client, space_id, doc_path, hierarchy, parent_cache
            )

            if page_id:
                # Update existing page
                existing = client.get_page_by_id(str(page_id))
                version = existing["version"]["number"]
                client.update_page(str(page_id), title, storage_body, version)
                updated += 1
                print(f"  Updated: {title}")
            else:
                # Create new page
                page = client.create_page(space_id, title, storage_body, parent_id)
                page_id = page["id"]
                created += 1
                print(f"  Created: {title} (id={page_id})")

            # Update frontmatter with sync info
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            update_frontmatter(doc_path, {
                "confluence_page_id": page_id,
                "last_synced": now,
            })

        except Exception as e:
            errors.append({"path": str(doc_path), "title": title, "error": str(e)})
            print(f"  ERROR: {title} - {e}", file=sys.stderr)

    print(f"\nSummary: {created} created, {updated} updated, {len(errors)} errors")


if __name__ == "__main__":
    main()
