# Confluence Migration

Migrate an unstructured legacy Confluence space into a structured, categorized new space using markdown as the source of truth.

## How it works

1. **Fetch** legacy pages as HTML snapshots (read-only, non-destructive)
2. **Discover** what's there — content distribution, taxonomy fit, ambiguous pages
3. **Restructure** pages into categorized markdown docs with frontmatter
4. **Validate** quality (frontmatter, required sections, broken links)
5. **Publish** to a new Confluence space (with preview and rollback)

Legacy pages are never modified or deleted. Every step is reversible.

## Setup

```bash
# Install dependencies (Python 3.11+)
uv pip install -e .

# Configure credentials
cp .env.example .env
# Edit .env with your Confluence URL, email, and API token
```

Edit `config/spaces.yaml` to set your legacy and destination space keys.

## Migration workflow

```bash
# 1. Snapshot legacy pages
python scripts/fetch_space.py

# 2. Analyze content — review the report before restructuring
python scripts/discover.py

# 3. Convert and classify into docs/ (via Claude Code skill)
#    /restructure

# 4. Validate docs
#    /validate

# 5. Preview and publish
python scripts/publish.py --preview     # inspect HTML locally
python scripts/publish.py --dry-run     # see what would happen
python scripts/publish.py               # publish to new space
python scripts/publish.py --rollback    # undo if needed
```

## Doc structure

```
docs/
  product/          Product vision, requirements (REQ-NNNN-*.md), user stories
  architecture/     System overview, ADRs (adrs/ADR-NNNN-*.md), module docs (modules/)
  runbooks/         Operational procedures, incident response, troubleshooting
  onboarding/       Developer setup, workflow guides
  api/              API reference, endpoint docs, integration guides
  infrastructure/   Cloud topology, CI/CD, monitoring
```

## Intelligent classification

Legacy pages are unstructured. The classifier detects page intent by analyzing **how content is written**, not just keywords:

- Steps + Prerequisites + Rollback -> Runbook
- `GET /api/...` + HTTP status codes -> API docs
- "As a user, I want..." + acceptance criteria -> Product requirement
- Context + Decision + Consequences -> Architecture/ADR
- Clone/install instructions -> Onboarding
- IaC tools, cloud services, monitoring -> Infrastructure

Classification rules: `config/taxonomy.yaml` (keywords) + `config/signals.yaml` (structural patterns).

## Config files

| File | Purpose |
|---|---|
| `config/spaces.yaml` | Confluence space keys and page hierarchy |
| `config/taxonomy.yaml` | Keyword rules for classifying pages |
| `config/signals.yaml` | Structural patterns for detecting content intent |
| `.env` | Confluence credentials (never committed) |

## Claude Code skills

If using [Claude Code](https://claude.ai/code), these skills automate the workflow:

| Skill | Purpose |
|---|---|
| `/fetch` | Pull legacy pages into `raw/` |
| `/discover` | Analyze content distribution and taxonomy fit |
| `/restructure` | Classify and place pages into `docs/` |
| `/validate` | Lint frontmatter and check quality |
| `/publish` | Push to new Confluence space |
| `/audit` | Gap analysis: legacy vs migrated |
| `/new-doc` | Scaffold a new doc from template |
