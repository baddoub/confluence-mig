Push docs from `docs/` to the new Confluence space. Non-destructive — only writes to the new space.

1. Run `python scripts/publish.py --preview` first — writes HTML to `preview/` for review.
2. Run `python scripts/publish.py --dry-run` to see what would be created/updated.
3. Run `python scripts/publish.py` to publish for real.
4. Run `python scripts/publish.py --rollback` to undo the last publish.

Only publishes docs with `status: published` or `status: review` in frontmatter. After publish, updates `confluence_page_id` and `last_synced` in each doc. Every run is logged to `raw/publish_log.json`.

Requires `.env` with `CONFLUENCE_URL`, `CONFLUENCE_EMAIL`, `CONFLUENCE_API_TOKEN`, and `NEW_SPACE_KEY`.
