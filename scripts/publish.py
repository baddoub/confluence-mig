"""Publish markdown docs from docs/ to the new Confluence space.

NON-DESTRUCTIVE: Legacy pages are never modified or deleted (unless --move).
All operations target the NEW space only. Every publish is logged to
raw/publish_log.json for rollback.

MODES:
  (default)     Create/update pages in the new space (legacy untouched)
  --move        Move legacy pages to new space + update content (preserves owner,
                history, comments, attachments). Rollback moves them back.
  --dry-run     Preview what would be created/updated/moved (no API calls)
  --preview     Dry-run + write converted HTML to preview/ for review
  --rollback    Undo the last publish run (delete created pages or move back)
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from html import escape as html_escape
from pathlib import Path

from scripts.confluence_client import ConfluenceClient
from scripts.utils import load_space_config, parse_frontmatter, update_frontmatter

DOCS_DIR = Path("docs")
PREVIEW_DIR = Path("preview")
PUBLISH_LOG_PATH = Path("raw") / "publish_log.json"


def markdown_to_confluence_storage(markdown_body: str) -> str:
    """Convert markdown body to Confluence storage format."""
    try:
        from md2cf.confluence_renderer import ConfluenceRenderer
        import mistune

        renderer = ConfluenceRenderer()
        md_parser = mistune.create_markdown(renderer=renderer)
        return md_parser(markdown_body)
    except ImportError:
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
    relative = doc_path.relative_to(DOCS_DIR)
    section = relative.parts[0] if len(relative.parts) > 1 else None

    if not section or section not in hierarchy:
        return None

    parent_title = hierarchy[section]

    if parent_title in parent_cache:
        return parent_cache[parent_title]

    results = client.search_pages(
        f'space.key="{space_id}" AND title="{parent_title}" AND type=page'
    )
    if results:
        parent_id = results[0]["id"]
        parent_cache[parent_title] = parent_id
        return parent_id

    page = client.create_page(
        space_id=space_id,
        title=parent_title,
        body=f"<p>Documentation section: {parent_title}</p>",
    )
    parent_id = page["id"]
    parent_cache[parent_title] = parent_id
    return parent_id


# --- Publish log for rollback ---

def load_publish_log() -> dict:
    """Load the publish log tracking all publish runs."""
    if PUBLISH_LOG_PATH.exists():
        return json.loads(PUBLISH_LOG_PATH.read_text(encoding="utf-8"))
    return {"runs": []}


def save_publish_log(log: dict):
    PUBLISH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    PUBLISH_LOG_PATH.write_text(json.dumps(log, indent=2), encoding="utf-8")


def do_preview(docs: list[Path]):
    """Convert docs to Confluence HTML and write to preview/ for inspection."""
    PREVIEW_DIR.mkdir(exist_ok=True)
    print(f"\nWriting preview to {PREVIEW_DIR}/\n")

    for doc_path in docs:
        meta, body = parse_frontmatter(doc_path)
        title = meta.get("title", doc_path.stem)
        action = "UPDATE" if meta.get("confluence_page_id") else "CREATE"

        storage_body = markdown_to_confluence_storage(body)

        # Wrap in a simple HTML page for easy browser preview
        safe_title = html_escape(title)
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{safe_title}</title>
<style>body {{ font-family: -apple-system, sans-serif; max-width: 800px; margin: 2em auto; padding: 0 1em; }}
table {{ border-collapse: collapse; }} td, th {{ border: 1px solid #ddd; padding: 6px 12px; }}
pre {{ background: #f4f4f4; padding: 1em; overflow-x: auto; }}
.meta {{ background: #e8f4e8; padding: 1em; border-radius: 4px; margin-bottom: 2em; font-size: 0.9em; }}
</style></head>
<body>
<div class="meta">
<strong>[{action}]</strong> {html_escape(str(doc_path))}<br>
Category: {html_escape(meta.get('category', '?'))} | Status: {html_escape(meta.get('status', '?'))} |
Legacy page: {html_escape(str(meta.get('legacy_page_id', 'none')))} |
Confluence page: {html_escape(str(meta.get('confluence_page_id', 'will be created')))}
</div>
<h1>{safe_title}</h1>
{storage_body}
</body></html>"""

        # Mirror the docs/ directory structure in preview/
        relative = doc_path.relative_to(DOCS_DIR)
        preview_path = PREVIEW_DIR / relative.with_suffix(".html")
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_text(html, encoding="utf-8")
        print(f"  [{action}] {title} -> {preview_path}")

    print(f"\nPreview written. Open files in {PREVIEW_DIR}/ to review before publishing.")


def do_rollback(client: ConfluenceClient):
    """Undo the last publish run: delete created pages, move back moved pages."""
    log = load_publish_log()
    if not log["runs"]:
        print("No publish runs to roll back.")
        return

    last_run = log["runs"][-1]
    if last_run.get("rolled_back"):
        print(f"Last run ({last_run['timestamp']}) was already rolled back.")
        return

    mode = last_run.get("mode", "create")
    created_pages = last_run.get("created_pages", [])
    moved_pages = last_run.get("moved_pages", [])

    if not created_pages and not moved_pages:
        print(f"Last run ({last_run['timestamp']}) has nothing to roll back.")
        return

    print(f"Rolling back {mode} run: {last_run['timestamp']}")

    removed = 0
    moved_back = 0
    errors = []

    # Roll back created pages (delete them)
    for page_info in reversed(created_pages):
        page_id = page_info["confluence_page_id"]
        title = page_info["title"]
        doc_path = Path(page_info["doc_path"])

        try:
            client.delete_page(page_id)
            removed += 1
            print(f"  Deleted: {title} (id={page_id})")

            if doc_path.exists():
                update_frontmatter(doc_path, {
                    "confluence_page_id": None,
                    "last_synced": None,
                })
        except Exception as e:
            errors.append({"page_id": page_id, "title": title, "error": str(e)})
            print(f"  ERROR: {title} - {e}", file=sys.stderr)

    # Roll back moved pages (move them back to original space)
    for page_info in reversed(moved_pages):
        page_id = page_info["page_id"]
        title = page_info["title"]
        doc_path = Path(page_info["doc_path"])
        original_space_key = page_info["original_space_key"]
        original_parent_id = page_info.get("original_parent_id")

        try:
            existing = client.get_page_by_id(page_id)
            version = existing["version"]["number"]

            # v2 API nests body under body.storage.value
            body_obj = existing.get("body", {})
            body = body_obj.get("storage", {}).get("value", "")
            client.move_page(
                page_id=page_id,
                target_space_key=original_space_key,
                title=title,
                body=body,
                version=version,
                parent_id=original_parent_id,
            )
            moved_back += 1
            print(f"  Moved back: {title} (id={page_id})")

            if doc_path.exists():
                update_frontmatter(doc_path, {
                    "confluence_page_id": None,
                    "last_synced": None,
                })
        except Exception as e:
            errors.append({"page_id": page_id, "title": title, "error": str(e)})
            print(f"  ERROR: {title} - {e}", file=sys.stderr)

    last_run["rolled_back"] = True
    last_run["rolled_back_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_publish_log(log)

    parts = []
    if removed:
        parts.append(f"{removed} deleted")
    if moved_back:
        parts.append(f"{moved_back} moved back")
    if errors:
        parts.append(f"{len(errors)} errors")
    print(f"\nRollback: {', '.join(parts)}")


def do_move(client: ConfluenceClient, target_space_id: str, target_space_key: str,
            legacy_space_key: str, hierarchy: dict, docs: list[Path]):
    """Move legacy pages to the new space and update their content.

    Preserves: owner, version history, comments, attachments.
    Only moves pages that have a legacy_page_id in frontmatter.
    Pages without legacy_page_id are created normally.
    """
    parent_cache: dict[str, str] = {}
    moved = 0
    created = 0
    errors = []

    run_record = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "move",
        "total_docs": len(docs),
        "moved_pages": [],
        "created_pages": [],
        "errors": [],
        "rolled_back": False,
    }

    for doc_path in docs:
        meta, body = parse_frontmatter(doc_path)
        title = meta.get("title", doc_path.stem)
        legacy_page_id = meta.get("legacy_page_id")

        try:
            storage_body = markdown_to_confluence_storage(body)
            parent_id = resolve_parent_page(
                client, target_space_id, doc_path, hierarchy, parent_cache
            )

            if legacy_page_id:
                # Move the existing legacy page to the new space
                existing = client.get_page_by_id(str(legacy_page_id))
                version = existing["version"]["number"]
                original_space_key = legacy_space_key
                original_parent_id = existing.get("parentId")

                client.move_page(
                    page_id=str(legacy_page_id),
                    target_space_key=target_space_key,
                    title=title,
                    body=storage_body,
                    version=version,
                    parent_id=parent_id,
                )
                moved += 1
                run_record["moved_pages"].append({
                    "page_id": str(legacy_page_id),
                    "title": title,
                    "doc_path": str(doc_path),
                    "original_space_key": original_space_key,
                    "original_parent_id": original_parent_id,
                    "previous_version": version,
                })
                print(f"  Moved: {title} (id={legacy_page_id}, v{version} -> v{version + 1})")

                now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                update_frontmatter(doc_path, {
                    "confluence_page_id": legacy_page_id,
                    "last_synced": now,
                })
            else:
                # No legacy page — create new
                page = client.create_page(target_space_id, title, storage_body, parent_id)
                page_id = page["id"]
                created += 1
                run_record["created_pages"].append({
                    "confluence_page_id": str(page_id),
                    "title": title,
                    "doc_path": str(doc_path),
                })
                print(f"  Created: {title} (id={page_id})")

                now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                update_frontmatter(doc_path, {
                    "confluence_page_id": page_id,
                    "last_synced": now,
                })

        except Exception as e:
            errors.append({"path": str(doc_path), "title": title, "error": str(e)})
            run_record["errors"].append(
                {"doc_path": str(doc_path), "title": title, "error": str(e)}
            )
            print(f"  ERROR: {title} - {e}", file=sys.stderr)

    log = load_publish_log()
    log["runs"].append(run_record)
    save_publish_log(log)

    print(f"\nSummary: {moved} moved, {created} created, {len(errors)} errors")
    print(f"Publish log: {PUBLISH_LOG_PATH}")
    if moved > 0 or created > 0:
        print("To undo: python scripts/publish.py --rollback")


def do_publish(client: ConfluenceClient, space_id: str, hierarchy: dict, docs: list[Path]):
    """Publish docs to the new Confluence space with full logging."""
    parent_cache: dict[str, str] = {}
    created = 0
    updated = 0
    errors = []

    # Track this run for rollback
    run_record = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_docs": len(docs),
        "created_pages": [],
        "updated_pages": [],
        "errors": [],
        "rolled_back": False,
    }

    for doc_path in docs:
        meta, body = parse_frontmatter(doc_path)
        title = meta.get("title", doc_path.stem)
        page_id = meta.get("confluence_page_id")

        try:
            storage_body = markdown_to_confluence_storage(body)
            parent_id = resolve_parent_page(
                client, space_id, doc_path, hierarchy, parent_cache
            )

            # Prepend original author info if available
            owner = meta.get("owner")
            if owner:
                owner_banner = (
                    '<ac:structured-macro ac:name="info">'
                    "<ac:rich-text-body>"
                    f"<p><strong>Original author:</strong> {html_escape(str(owner))}</p>"
                    "</ac:rich-text-body>"
                    "</ac:structured-macro>"
                )
                storage_body = owner_banner + storage_body

            if page_id:
                # Update existing page — save previous version number for rollback
                existing = client.get_page_by_id(str(page_id))
                version = existing["version"]["number"]
                client.update_page(str(page_id), title, storage_body, version)
                updated += 1
                run_record["updated_pages"].append({
                    "confluence_page_id": str(page_id),
                    "title": title,
                    "doc_path": str(doc_path),
                    "previous_version": version,
                })
                print(f"  Updated: {title} (version {version} -> {version + 1})")
            else:
                # Create new page in the NEW space (legacy is untouched)
                page = client.create_page(space_id, title, storage_body, parent_id)
                page_id = page["id"]
                created += 1
                run_record["created_pages"].append({
                    "confluence_page_id": str(page_id),
                    "title": title,
                    "doc_path": str(doc_path),
                })
                print(f"  Created: {title} (id={page_id})")

            # Update frontmatter with sync info
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            update_frontmatter(doc_path, {
                "confluence_page_id": page_id,
                "last_synced": now,
            })

        except Exception as e:
            errors.append({"path": str(doc_path), "title": title, "error": str(e)})
            run_record["errors"].append({"doc_path": str(doc_path), "title": title, "error": str(e)})
            print(f"  ERROR: {title} - {e}", file=sys.stderr)

    # Save publish log
    log = load_publish_log()
    log["runs"].append(run_record)
    save_publish_log(log)

    print(f"\nSummary: {created} created, {updated} updated, {len(errors)} errors")
    print(f"Publish log: {PUBLISH_LOG_PATH}")
    if created > 0:
        print("To undo: python scripts/publish.py --rollback")


def main():
    parser = argparse.ArgumentParser(description="Publish docs to Confluence (non-destructive)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be published")
    parser.add_argument("--preview", action="store_true", help="Dry-run + write HTML preview files")
    parser.add_argument("--move", action="store_true",
                        help="Move legacy pages to new space (preserves owner/history/comments)")
    parser.add_argument("--rollback", action="store_true", help="Undo last publish run")
    args = parser.parse_args()

    config = load_space_config()
    new_key = config["new"]["space_key"]
    legacy_key = config["legacy"]["space_key"]
    hierarchy = config["new"].get("hierarchy", {})

    if args.preview:
        docs = find_publishable_docs()
        if not docs:
            print("No docs with status 'published' or 'review' found.")
            return
        print(f"Found {len(docs)} docs to preview")
        do_preview(docs)
        return

    client = ConfluenceClient()

    if args.rollback:
        do_rollback(client)
        return

    new_space = client.get_space_by_key(new_key)
    new_space_id = str(new_space["id"])

    docs = find_publishable_docs()
    if not docs:
        print("No docs with status 'published' or 'review' found.")
        return

    print(f"Found {len(docs)} docs to publish")

    if args.dry_run:
        for doc in docs:
            meta, _ = parse_frontmatter(doc)
            has_legacy = bool(meta.get("legacy_page_id"))
            if args.move and has_legacy:
                action = "MOVE"
            elif meta.get("confluence_page_id"):
                action = "UPDATE"
            else:
                action = "CREATE"
            print(f"  [{action}] {meta.get('title', doc.stem)} ({doc})")
        mode_hint = " --move" if args.move else ""
        print(f"\nTo publish for real: python scripts/publish.py{mode_hint}")
        return

    if args.move:
        legacy_space = client.get_space_by_key(legacy_key)
        print(f"Moving from: {legacy_space['name']} (key={legacy_key})")
        print(f"Moving to:   {new_space['name']} (key={new_key})")
        do_move(client, new_space_id, new_key, legacy_key, hierarchy, docs)
    else:
        print(f"Publishing to: {new_space['name']} (key={new_key})")
        do_publish(client, new_space_id, hierarchy, docs)


if __name__ == "__main__":
    main()
