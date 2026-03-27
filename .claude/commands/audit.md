Compare legacy Confluence pages against migrated docs to find gaps.

1. Run `python scripts/audit.py` or read the files directly.
2. Cross-references `raw/current/*.meta.json` (legacy pages) against `docs/**/*.md` frontmatter (`legacy_page_id`).

Reports: unmigrated pages, drafts needing review, orphaned docs (no legacy source), category breakdown, and coverage percentage.

If `raw/current/` is empty, remind user to run `/fetch` first.
