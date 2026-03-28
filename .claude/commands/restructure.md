Classify and reorganize fetched content from `raw/current/` into the `docs/` taxonomy.

Legacy pages are unstructured — detect their intent by **how they're written**, not just keywords:

| Content pattern | Detected as |
|---|---|
| Steps + Prerequisites + Rollback | Runbook |
| `GET /api/...`, HTTP status codes | API docs |
| "As a user, I want..." + acceptance criteria | Product requirement |
| Context + Decision + Consequences | Architecture/ADR |
| Clone/install instructions | Onboarding |
| IaC tools, cloud services, monitoring | Infrastructure |

**Process each page:**
1. Convert HTML to markdown via `scripts/convert.py`.
2. Run `classify_page()` from `scripts/taxonomy.py` — returns category, confidence, subcategory, and mixed intents.
3. **High confidence (>=0.7):** place directly. **Low confidence (<0.5):** read the content yourself and decide. **Mixed intent (should_split):** split into separate docs per detected topic.
4. Add frontmatter, generate kebab-case filename, place in the correct `docs/` subdirectory. Set `owner` from `.meta.json` `authorName` field, and `legacy_page_id` from `id`.
5. ADRs → `ADR-NNNN-slug.md`, requirements → `REQ-NNNN-slug.md`.

**Skip** empty pages, pure link pages, and table-of-contents pages.

Report: pages per category, splits performed, ambiguous pages with reasoning.
