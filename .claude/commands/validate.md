Lint all docs in `docs/` for quality.

Check each markdown file for:

1. **Frontmatter**: all required fields present (`title`, `category`, `status`, `created`, `updated`), valid values.
2. **Template compliance**:
   - Product requirements → must have "User Story", "Acceptance Criteria", "Status"
   - ADRs → must have "Status", "Context", "Decision", "Consequences"
   - Runbooks → must have "Prerequisites", "Steps", "Rollback"
3. **Links**: relative links resolve to existing files; flag old `confluence://` links.

Report a summary table with pass/fail per check per file. Fix straightforward issues (missing dates, incomplete frontmatter) directly.
