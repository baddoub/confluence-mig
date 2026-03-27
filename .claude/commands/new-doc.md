Scaffold a new document from a template.

## Steps

1. Ask the user for:
   - **Category**: product, architecture, runbook, onboarding, api, or infrastructure
   - **Title**: The document title
   - **Type** (if applicable): For architecture, ask if it's an ADR or service overview. For product, ask if it's a requirement.

2. Based on the category and type, copy the appropriate template from `templates/`:
   - Product requirement → `templates/product-requirement.md`
   - ADR → `templates/adr.md`
   - Service doc → `templates/service-overview.md`
   - Runbook → `templates/runbook.md`
   - Onboarding → `templates/onboarding-guide.md`
   - API reference → `templates/api-reference.md`

3. Generate the filename:
   - Convert title to `lowercase-kebab-case.md`
   - For ADRs: find the next available number and name as `ADR-NNNN-slug.md`
   - For requirements: find the next available number and name as `REQ-NNNN-slug.md`

4. Fill in the frontmatter:
   - Set `title` to the provided title
   - Set `category` to the selected category
   - Set `status` to `draft`
   - Set `created` and `updated` to today's date

5. Place the file in the correct directory:
   - Product requirements → `docs/product/requirements/`
   - ADRs → `docs/architecture/adrs/`
   - Service docs → `docs/architecture/services/`
   - Runbooks → `docs/runbooks/` (ask for subdirectory: incident-response, deployment, troubleshooting)
   - Onboarding → `docs/onboarding/`
   - API → `docs/api/endpoints/`
   - Infrastructure → `docs/infrastructure/`

6. Report the created file path and remind the user to fill in the content.
