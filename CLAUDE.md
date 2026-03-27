# Confluence Migration — Docs-as-Code

This repo migrates a legacy Confluence space into structured, categorized markdown documentation and publishes it back to a new Confluence space. It serves as both the **source of truth** for docs and the **automation tooling** for the migration.

## Product Context

`docs/product/` is the anchor for all documentation. It defines what the product is, who it's for, and what it does. All other sections reference this context. Product details are extracted from the legacy Confluence space during `/fetch`.

## Doc Taxonomy

| Directory | What goes here |
|---|---|
| `docs/product/` | Product vision, feature requirements (`REQ-NNNN-*.md`), user stories, roadmap |
| `docs/architecture/` | System design, service docs, ADRs (`ADR-NNNN-*.md`) |
| `docs/runbooks/` | Operational procedures, incident response, troubleshooting guides |
| `docs/onboarding/` | Developer setup, workflow guides, environment descriptions |
| `docs/api/` | API reference, endpoint docs, integration guides |
| `docs/infrastructure/` | Cloud topology, CI/CD pipelines, monitoring & observability |

## Frontmatter Schema

Every markdown file in `docs/` must start with this YAML frontmatter:

```yaml
---
title: "Page Title"
category: product | architecture | runbook | onboarding | api | infrastructure
status: draft | review | published
owner: ""
tags: []
confluence_page_id: null
legacy_page_id: null
last_synced: null
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

## Naming Conventions

- **Filenames**: `lowercase-kebab-case.md`
- **ADRs**: `ADR-NNNN-short-title.md` (e.g., `ADR-0001-use-postgres.md`)
- **Requirements**: `REQ-NNNN-short-title.md` (e.g., `REQ-0001-user-auth.md`)
- **Links**: Always use relative markdown links (e.g., `../architecture/overview.md`)

## Templates

New docs must start from a template in `templates/`:

| Template | Use for |
|---|---|
| `product-requirement.md` | Feature specs, user stories |
| `adr.md` | Architecture Decision Records |
| `service-overview.md` | Service/component documentation |
| `runbook.md` | Operational procedures |
| `onboarding-guide.md` | Onboarding & setup guides |
| `api-reference.md` | API endpoint documentation |

## Quality Rules

- **Product requirements**: Must have "User Story", "Acceptance Criteria", "Status" sections
- **Runbooks**: Must have "Prerequisites", "Steps", "Rollback" sections
- **ADRs**: Must have "Status", "Context", "Decision", "Consequences" sections
- **All docs**: Must have complete frontmatter, no broken relative links

## Available Skills

| Skill | Purpose |
|---|---|
| `/fetch` | Pull pages from legacy Confluence space into `raw/` |
| `/restructure` | Classify and reorganize fetched content into `docs/` taxonomy |
| `/publish` | Push docs back to new Confluence space |
| `/audit` | Gap analysis: legacy pages vs migrated docs |
| `/validate` | Lint frontmatter, check template compliance, find broken links |
| `/new-doc` | Scaffold a new doc from template |

## Scripts

All scripts are in `scripts/`. Requires Python 3.11+ with dependencies from `pyproject.toml`.

```bash
# Install dependencies
uv pip install -e .

# Copy and fill in environment variables
cp .env.example .env

# Fetch legacy pages
python scripts/fetch_space.py

# Convert fetched HTML to markdown
python scripts/convert.py

# Publish to new Confluence space
python scripts/publish.py

# Run gap audit
python scripts/audit.py
```

## Config

- `config/spaces.yaml` — Confluence space keys and hierarchy mapping
- `config/taxonomy.yaml` — Keyword/pattern rules for classifying pages into categories
- `.env` — Credentials (never committed)
