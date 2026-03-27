Fetch all pages from the legacy Confluence space into the `raw/` directory.

## Steps

1. Read `config/spaces.yaml` to get the legacy space key and optional root page ID.
2. Run `python scripts/fetch_space.py` to call the Confluence Cloud REST API v2 with cursor-based pagination.
3. Each page is saved as:
   - `raw/{page_id}_{slug}.html` — the page body in Confluence storage format
   - `raw/{page_id}_{slug}.meta.json` — metadata (title, parent ID, labels, last modified, author)
4. If a `root_page_id` is set in spaces.yaml, only fetch that page and its descendants.
5. Report a summary: total pages fetched, any errors, and a list of page titles with their IDs.

## Environment

Requires `.env` with `CONFLUENCE_URL`, `CONFLUENCE_EMAIL`, and `CONFLUENCE_API_TOKEN`.

## Notes

- Uses cursor-based pagination (REST API v2) for efficient traversal of large spaces.
- Skips pages that haven't changed since the last fetch (compares `raw/*.meta.json` timestamps).
- If the script doesn't exist or has errors, fix it before running.
