Scaffold a new doc from a template.

1. Ask for **category** (product, architecture, runbook, onboarding, api, infrastructure) and **title**.
2. For architecture: ask if ADR or module doc. For product: ask if requirement.
3. Copy the matching template from `templates/`, fill in frontmatter (`title`, `category`, `status: draft`, today's date).
4. Generate filename: `lowercase-kebab-case.md`. ADRs: `ADR-NNNN-slug.md`. Requirements: `REQ-NNNN-slug.md` (auto-increment NNNN).
5. Place in the correct `docs/` subdirectory.

Template mapping:
- Product requirement → `templates/product-requirement.md` → `docs/product/requirements/`
- ADR → `templates/adr.md` → `docs/architecture/adrs/`
- Module doc → `templates/module-overview.md` → `docs/architecture/modules/`
- Runbook → `templates/runbook.md` → `docs/runbooks/{incident-response|deployment|troubleshooting}/`
- Onboarding → `templates/onboarding-guide.md` → `docs/onboarding/`
- API → `templates/api-reference.md` → `docs/api/endpoints/`
- Infrastructure → (no template, use blank frontmatter) → `docs/infrastructure/`
