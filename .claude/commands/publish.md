Push restructured markdown docs from `docs/` back to the new Confluence space.

## Steps

1. Read `config/spaces.yaml` to get the new space key and parent page hierarchy mapping.
2. Scan `docs/` for all markdown files with `status: published` or `status: review` in frontmatter.
3. For each doc:
   - Convert markdown to Confluence storage format using `md2cf` or `scripts/publish.py`
   - Determine the parent page based on the file's directory (using hierarchy mapping from spaces.yaml)
   - If `confluence_page_id` exists in frontmatter, **update** the existing page
   - If `confluence_page_id` is null, **create** a new page
4. After successful publish, update the doc's frontmatter:
   - Set `confluence_page_id` to the new/updated page ID
   - Set `last_synced` to current timestamp
   - Set `status` to `published` (if it was `review`)
5. Report:
   - Pages created vs updated
   - Any errors (permission issues, API failures)
   - Links to the published pages

## Environment

Requires `.env` with `CONFLUENCE_URL`, `CONFLUENCE_EMAIL`, `CONFLUENCE_API_TOKEN`, and `NEW_SPACE_KEY`.

## Notes

- Respects the parent-child hierarchy defined in `config/spaces.yaml`.
- Creates top-level parent pages (Product, Architecture, Runbooks, etc.) if they don't exist.
- Converts relative markdown links to Confluence page links where possible.
