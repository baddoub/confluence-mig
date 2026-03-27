"""Fetch all pages from a legacy Confluence space into raw/.

NON-DESTRUCTIVE: Legacy pages are READ-ONLY — never modified or deleted.
Each fetch creates a timestamped snapshot in raw/snapshots/ so previous
fetches are preserved for rollback.
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.confluence_client import ConfluenceClient
from scripts.utils import load_space_config, slugify

RAW_DIR = Path("raw")
SNAPSHOTS_DIR = RAW_DIR / "snapshots"
CURRENT_DIR = RAW_DIR / "current"
MANIFEST_PATH = RAW_DIR / "manifest.json"


def fetch_page_with_body(client: ConfluenceClient, page_id: str) -> dict:
    """Fetch a page including its storage-format body."""
    return client.get_page_by_id(page_id, body_format="storage")


def save_page(page: dict, labels: list[str], output_dir: Path) -> Path:
    """Save a page's HTML body and metadata sidecar."""
    page_id = page["id"]
    title = page.get("title", "untitled")
    slug = slugify(title)
    prefix = f"{page_id}_{slug}"

    body = page.get("body", {}).get("storage", {}).get("value", "")
    html_path = output_dir / f"{prefix}.html"
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
    meta_path = output_dir / f"{prefix}.meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return html_path


def should_skip(page_id: str, slug: str, output_dir: Path) -> bool:
    """Check if a page was already fetched (for incremental fetches)."""
    prefix = f"{page_id}_{slug}"
    return (
        (output_dir / f"{prefix}.html").exists()
        and (output_dir / f"{prefix}.meta.json").exists()
    )


def create_snapshot(timestamp: str) -> Path:
    """Create a timestamped snapshot directory."""
    snapshot_dir = SNAPSHOTS_DIR / timestamp
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    return snapshot_dir


def update_current_symlink(snapshot_dir: Path):
    """Point raw/current/ at the latest snapshot (copy, not symlink, for portability)."""
    if CURRENT_DIR.exists():
        shutil.rmtree(CURRENT_DIR)
    shutil.copytree(snapshot_dir, CURRENT_DIR)


def save_manifest(manifest: dict):
    """Save the fetch manifest tracking all snapshots."""
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def load_manifest() -> dict:
    """Load the fetch manifest."""
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {"snapshots": [], "legacy_space_key": None, "legacy_space_name": None}


def main():
    parser = argparse.ArgumentParser(description="Fetch legacy Confluence space (non-destructive)")
    parser.add_argument("--dry-run", action="store_true", help="List pages without downloading")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if already downloaded")
    parser.add_argument(
        "--restore", metavar="TIMESTAMP",
        help="Restore raw/current/ from a previous snapshot (e.g., 2026-03-27T120000Z)",
    )
    args = parser.parse_args()

    manifest = load_manifest()

    # Handle restore from previous snapshot
    if args.restore:
        snapshot_dir = SNAPSHOTS_DIR / args.restore
        if not snapshot_dir.exists():
            print(f"Snapshot not found: {snapshot_dir}")
            print("Available snapshots:")
            for snap in sorted(SNAPSHOTS_DIR.iterdir()):
                if snap.is_dir():
                    print(f"  {snap.name}")
            sys.exit(1)
        update_current_symlink(snapshot_dir)
        print(f"Restored raw/current/ from snapshot: {args.restore}")
        return

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

    # Create a new timestamped snapshot
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    snapshot_dir = create_snapshot(timestamp)
    print(f"Snapshot: {snapshot_dir}")

    RAW_DIR.mkdir(exist_ok=True)
    fetched = 0
    skipped = 0
    errors = []

    for page_summary in pages:
        page_id = page_summary["id"]
        title = page_summary.get("title", "untitled")
        slug = slugify(title)

        if not args.force and should_skip(page_id, slug, snapshot_dir):
            skipped += 1
            continue

        try:
            page = fetch_page_with_body(client, page_id)
            labels = client.get_page_labels(page_id)
            save_page(page, labels, snapshot_dir)
            fetched += 1
            print(f"  Fetched: {title}")
        except Exception as e:
            errors.append({"page_id": page_id, "title": title, "error": str(e)})
            print(f"  ERROR: {title} - {e}", file=sys.stderr)

    # Update current/ to point to this snapshot
    update_current_symlink(snapshot_dir)

    # Update manifest
    manifest["legacy_space_key"] = legacy_key
    manifest["legacy_space_name"] = space["name"]
    manifest["snapshots"].append({
        "timestamp": timestamp,
        "pages_fetched": fetched,
        "pages_skipped": skipped,
        "errors": len(errors),
        "total_pages": len(pages),
    })
    save_manifest(manifest)

    print(f"\nSummary: {fetched} fetched, {skipped} skipped, {len(errors)} errors")
    print(f"Snapshot saved to: {snapshot_dir}")
    print(f"Current data: {CURRENT_DIR}")
    if manifest["snapshots"]:
        print(f"Total snapshots: {len(manifest['snapshots'])} "
              f"(restore with --restore TIMESTAMP)")
    if errors:
        print("Errors:")
        for err in errors:
            print(f"  [{err['page_id']}] {err['title']}: {err['error']}")


if __name__ == "__main__":
    main()
