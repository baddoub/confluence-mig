Validate all documentation in `docs/` for quality and compliance.

## Steps

1. Scan all markdown files in `docs/`.
2. For each file, check:

### Frontmatter Validation
- All required fields present: `title`, `category`, `status`, `owner`, `tags`, `created`, `updated`
- `category` is one of: product, architecture, runbook, onboarding, api, infrastructure
- `status` is one of: draft, review, published
- `created` and `updated` are valid dates

### Template Compliance
- **Product requirements** (`docs/product/requirements/`): Must have "User Story", "Acceptance Criteria", "Status" sections
- **ADRs** (`docs/architecture/adrs/`): Must have "Status", "Context", "Decision", "Consequences" sections
- **Runbooks** (`docs/runbooks/`): Must have "Prerequisites", "Steps", "Rollback" sections
- **All docs**: Must have at least an H1 heading matching the title

### Link Validation
- Check all relative markdown links resolve to existing files
- Flag any absolute URLs that point to the old Confluence space

3. Report per-file results and an overall quality score:

```
| File                        | Frontmatter | Template | Links | Score |
|-----------------------------|-------------|----------|-------|-------|
| docs/runbooks/deploy.md     | PASS        | FAIL     | PASS  | 67%   |
```

## Notes

- Run this before `/publish` to catch issues early.
- Fix issues directly when they're straightforward (missing dates, incomplete frontmatter).
