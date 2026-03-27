Fetch all pages from the legacy Confluence space into `raw/`. Non-destructive — legacy pages are read-only.

1. Read `config/spaces.yaml` for the legacy space key.
2. Run `python scripts/fetch_space.py` to pull all pages via Confluence REST API v2.
3. Pages are saved to a timestamped snapshot in `raw/snapshots/`. `raw/current/` points to the latest.

**Flags:**
- `--dry-run` — list pages without downloading
- `--force` — re-fetch already downloaded pages
- `--restore TIMESTAMP` — revert `raw/current/` to a previous snapshot

Requires `.env` with `CONFLUENCE_URL`, `CONFLUENCE_EMAIL`, `CONFLUENCE_API_TOKEN`.
