"""Gap analysis: compare legacy pages in raw/ against migrated docs in docs/."""

import json
from pathlib import Path

import yaml

RAW_DIR = Path("raw/current")
RAW_DIR_FALLBACK = Path("raw")
DOCS_DIR = Path("docs")


def load_legacy_pages() -> list[dict]:
    """Load metadata for all fetched legacy pages."""
    source_dir = RAW_DIR if RAW_DIR.exists() else RAW_DIR_FALLBACK
    pages = []
    for meta_path in sorted(source_dir.glob("*.meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        pages.append(meta)
    return pages


def parse_frontmatter(filepath: Path) -> dict:
    """Parse YAML frontmatter from a markdown file."""
    text = filepath.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def load_migrated_docs() -> list[dict]:
    """Load frontmatter from all docs."""
    docs = []
    for md_file in sorted(DOCS_DIR.rglob("*.md")):
        meta = parse_frontmatter(md_file)
        meta["_path"] = str(md_file)
        docs.append(meta)
    return docs


def run_audit():
    """Run the gap analysis and print results."""
    legacy = load_legacy_pages()
    docs = load_migrated_docs()

    if not legacy:
        print("No legacy pages found in raw/. Run /fetch first.")
        return

    # Build lookup sets
    legacy_ids = {str(p["id"]) for p in legacy}
    migrated_ids = {
        str(d["legacy_page_id"]) for d in docs if d.get("legacy_page_id")
    }

    # Classify
    unmigrated = [p for p in legacy if str(p["id"]) not in migrated_ids]
    drafts = [d for d in docs if d.get("status") == "draft"]
    orphaned = [
        d for d in docs
        if not d.get("legacy_page_id") and d.get("_path", "").startswith("docs/")
    ]

    # Category breakdown
    category_counts: dict[str, int] = {}
    for d in docs:
        cat = d.get("category", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Print report
    print("=" * 60)
    print("MIGRATION AUDIT REPORT")
    print("=" * 60)

    print(f"\nTotal legacy pages: {len(legacy)}")
    print(f"Total migrated docs: {len(docs)}")
    print(f"Migration coverage: {len(migrated_ids)}/{len(legacy_ids)} "
          f"({100 * len(migrated_ids) / len(legacy_ids):.0f}%)" if legacy_ids else "N/A")

    print("\n--- Category Breakdown ---")
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat}: {count}")

    if unmigrated:
        print(f"\n--- Unmigrated Pages ({len(unmigrated)}) ---")
        for p in unmigrated:
            print(f"  [{p['id']}] {p['title']}")

    if drafts:
        print(f"\n--- Drafts Needing Review ({len(drafts)}) ---")
        for d in drafts:
            print(f"  {d.get('_path', 'unknown')}: {d.get('title', 'untitled')}")

    if orphaned:
        print(f"\n--- Orphaned Docs (no legacy_page_id) ({len(orphaned)}) ---")
        for d in orphaned:
            print(f"  {d.get('_path', 'unknown')}: {d.get('title', 'untitled')}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_audit()
