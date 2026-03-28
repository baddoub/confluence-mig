Push docs from `docs/` to the new Confluence space.

**Two modes:**
- **Create (default):** creates new pages in the new space. Legacy untouched.
- **Move (`--move`):** moves legacy pages to the new space and updates content. Preserves owner, version history, comments, and attachments.

**Workflow:**
1. `python scripts/publish.py --preview` — writes HTML to `preview/` for review
2. `python scripts/publish.py --dry-run` — shows CREATE/UPDATE/MOVE plan
3. `python scripts/publish.py` or `python scripts/publish.py --move` — execute
4. `python scripts/publish.py --rollback` — undo (deletes created pages or moves back)

Only publishes docs with `status: published` or `status: review`. Every run is logged to `raw/publish_log.json`.

Requires `.env` with `CONFLUENCE_URL`, `CONFLUENCE_EMAIL`, `CONFLUENCE_API_TOKEN`.
