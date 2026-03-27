Perform a gap analysis comparing legacy Confluence pages against the migrated docs in `docs/`.

## Steps

1. Scan `raw/*.meta.json` to build a list of all legacy pages (ID, title, labels).
2. Scan all markdown files in `docs/` and collect their `legacy_page_id` frontmatter values.
3. Cross-reference to identify:
   - **Unmigrated pages**: Legacy pages with no corresponding doc in `docs/`
   - **Stale content**: Docs where legacy page was updated after `last_synced`
   - **Orphaned docs**: Files in `docs/` with no `legacy_page_id` that weren't manually created
   - **Incomplete migrations**: Docs with `status: draft` that need review
4. Run `scripts/audit.py` if it exists, or perform the analysis by reading the files directly.
5. Report a summary table:

```
| Category        | Count | Details          |
|-----------------|-------|------------------|
| Migrated        | N     | ...              |
| Unmigrated      | N     | list of titles   |
| Stale           | N     | list of titles   |
| Draft (review)  | N     | list of titles   |
| Total Legacy    | N     |                  |
```

## Notes

- If `raw/` is empty, remind the user to run `/fetch` first.
- Flag any legacy pages that were split into multiple docs during restructure.
