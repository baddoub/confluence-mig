Classify and reorganize fetched legacy content from `raw/` into the structured `docs/` taxonomy.

## Steps

1. Read all raw pages from `raw/` (both `.html` and `.meta.json` files).
2. Convert each HTML page to markdown using `scripts/convert.py` (BeautifulSoup + markdownify).
3. Classify each page into a category using:
   - Rules from `config/taxonomy.yaml` (keyword and pattern matching)
   - Your own judgment for ambiguous pages based on content analysis
4. For each classified page:
   - Generate a kebab-case filename from the page title
   - Add proper YAML frontmatter (title, category, status: draft, legacy_page_id, dates)
   - Place the file in the appropriate `docs/` subdirectory
   - For requirements, name as `REQ-NNNN-slug.md`; for ADRs, name as `ADR-NNNN-slug.md`
5. Extract product context (product name, description, users) from relevant pages and populate `docs/product/overview.md`.
6. Report:
   - Pages per category breakdown
   - Any pages that were ambiguous (flagged for manual review)
   - Any pages that didn't match any taxonomy rules

## Notes

- Prefer splitting long legacy pages into multiple focused docs over keeping monolithic pages.
- Preserve internal links — update them to use relative markdown links.
- If a page contains mixed content (e.g., runbook + architecture), split into separate docs.
- Content that looks like a product overview, vision, or description should go to `docs/product/`.
