Classify and reorganize fetched legacy content from `raw/` into the structured `docs/` taxonomy.

Legacy pages are often unstructured — vague titles like "Notes", "Process", or "Team Stuff", with mixed content that spans multiple categories. The classification system detects intent using three layers:

1. **Keyword/pattern matching** from `config/taxonomy.yaml`
2. **Structural intent detection** — analyzes HOW the page is written (numbered steps = runbook, HTTP methods = API docs, user story format = product requirement, decision language = ADR, etc.)
3. **Content-section analysis** — detects when a single page covers multiple topics and should be split

## Steps

1. Read all raw pages from `raw/` (both `.html` and `.meta.json` files).
2. Convert each HTML page to markdown using `scripts/convert.py` (BeautifulSoup + markdownify).
3. Classify each page by running `scripts/taxonomy.py`'s `classify_page()` function, which returns:
   - `category` — best-fit category
   - `confidence` — 0.0 to 1.0 confidence score
   - `signals` — human-readable reasons for the classification
   - `suggested_subcategory` — specific subdirectory (e.g., `incident-response`, `adrs`, `endpoints`)
   - `mixed_intents` — list of detected topics if the page should be split
4. Handle results based on confidence and intent:

   **High confidence (>=0.7)**: Place directly in the target directory.

   **Medium confidence (0.5–0.7)**: Place in target directory but add `status: draft` and a `<!-- REVIEW: classification signals -->` comment at the top for human review.

   **Low confidence (<0.5)**: Use YOUR OWN judgment. Read the content yourself, understand what it's about, and classify it. Add a comment explaining your reasoning.

   **Mixed-intent pages (should_split=true)**: Split the page into multiple docs, one per detected intent. Each split doc gets:
   - Its own frontmatter with the correct category
   - A note referencing the original legacy page
   - A `<!-- SPLIT: from original page "Page Title" -->` comment

5. For each classified page:
   - Generate a kebab-case filename from the page title
   - Add proper YAML frontmatter: title, category, status, legacy_page_id, created/updated dates
   - Use the `suggested_subcategory` to route to the right subdirectory (e.g., `docs/runbooks/incident-response/` vs `docs/runbooks/deployment/`)
   - For requirements, name as `REQ-NNNN-slug.md`; for ADRs, name as `ADR-NNNN-slug.md`

6. Extract product context (product name, description, users) from relevant pages and populate `docs/product/overview.md`.

7. Report:
   - Pages per category breakdown with confidence levels
   - Pages that were split (what original became what docs)
   - Ambiguous pages (low confidence) and the reasoning for their placement
   - Any pages that had no detectable intent (truly unclassifiable)

## Structural signals the classifier looks for

| Signal | Indicates | Example |
|---|---|---|
| Numbered step headings (`## Step 1`) | Runbook | Deployment procedure |
| Prerequisites/Rollback sections | Runbook | Operational procedure |
| CLI commands (`kubectl`, `ssh`, `docker`) | Runbook | Ops procedure |
| HTTP methods + paths (`GET /api/...`) | API docs | Endpoint reference |
| HTTP status codes (200, 404, 500) | API docs | API response docs |
| User story format ("As a... I want...") | Product | Feature requirement |
| Decision language ("we decided", "trade-off") | Architecture/ADR | Design decision |
| Dependency language ("calls", "upstream") | Architecture | System design |
| Clone/install instructions | Onboarding | Dev setup guide |
| IaC tools (Terraform, Helm, Docker) | Infrastructure | Platform docs |
| Monitoring tools (Grafana, Datadog) | Infrastructure | Observability |

## Notes

- **Trust structure over titles**: A page called "Important Notes" that contains rollback steps and kubectl commands is a runbook, not architecture.
- Prefer splitting long legacy pages into multiple focused docs over keeping monolithic pages.
- Preserve internal links — update `confluence://Page Title` links to relative markdown links where the target page has been migrated.
- If a page is mostly empty, a table of contents, or just links to other pages, skip it (don't migrate placeholder pages).
- Content that looks like a product overview, vision, or description should go to `docs/product/`.
