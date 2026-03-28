"""Validate docs in docs/ for frontmatter, template compliance, and broken links."""

import re
import sys
from pathlib import Path

from scripts.utils import parse_frontmatter

DOCS_DIR = Path("docs")

REQUIRED_FRONTMATTER = {"title", "category", "status", "created", "updated"}
VALID_CATEGORIES = {"product", "architecture", "runbook", "onboarding", "api", "infrastructure"}
VALID_STATUSES = {"draft", "review", "published"}

# Required sections by category (heading text must contain these)
REQUIRED_SECTIONS = {
    "product": ["user story", "acceptance criteria", "status"],
    "runbook": ["prerequisites", "steps", "rollback"],
    "architecture": [],  # ADRs checked separately via filename prefix
}
ADR_SECTIONS = ["status", "context", "decision", "consequences"]


def _extract_headings(body: str) -> list[str]:
    """Extract all markdown headings as lowercase strings."""
    return [m.group(1).strip().lower() for m in re.finditer(r"^#{1,4}\s+(.+)$", body, re.MULTILINE)]


def _extract_relative_links(body: str) -> list[str]:
    """Extract all relative markdown links (not http/https/confluence://)."""
    links = re.findall(r"\[.*?\]\(([^)]+)\)", body)
    return [link for link in links if not link.startswith(("http://", "https://", "confluence://", "#"))]


def validate_file(filepath: Path) -> list[str]:
    """Validate a single doc file. Returns list of error strings."""
    errors = []
    meta, body = parse_frontmatter(filepath)

    # 1. Frontmatter completeness
    if not meta:
        errors.append("missing frontmatter entirely")
        return errors

    for field in REQUIRED_FRONTMATTER:
        if not meta.get(field):
            errors.append(f"missing required field: {field}")

    category = meta.get("category", "")
    if category and category not in VALID_CATEGORIES:
        errors.append(f"invalid category: {category}")

    status = meta.get("status", "")
    if status and status not in VALID_STATUSES:
        errors.append(f"invalid status: {status}")

    # 2. Template compliance — required sections
    headings = _extract_headings(body)

    if filepath.name.startswith("ADR-"):
        for section in ADR_SECTIONS:
            if not any(section in h for h in headings):
                errors.append(f"ADR missing section: {section}")
    elif category in REQUIRED_SECTIONS:
        for section in REQUIRED_SECTIONS[category]:
            if not any(section in h for h in headings):
                errors.append(f"missing required section: {section}")

    # 3. Relative links resolve
    for link in _extract_relative_links(body):
        link_path = link.split("#")[0]  # strip anchor
        if not link_path:
            continue
        target = (filepath.parent / link_path).resolve()
        if not target.exists():
            errors.append(f"broken link: {link}")

    # 4. Flag legacy confluence:// links
    confluence_links = re.findall(r"confluence://[^\s)]+", body)
    for link in confluence_links:
        errors.append(f"unresolved confluence link: {link}")

    return errors


def main():
    if not DOCS_DIR.exists():
        print("No docs/ directory found. Nothing to validate.")
        return

    files = sorted(DOCS_DIR.rglob("*.md"))
    if not files:
        print("No markdown files found in docs/.")
        return

    total_errors = 0
    results = []

    for filepath in files:
        errors = validate_file(filepath)
        rel = filepath.relative_to(DOCS_DIR)
        status = "FAIL" if errors else "PASS"
        results.append((rel, status, errors))
        total_errors += len(errors)

    # Print summary table
    print("=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)

    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    print(f"\n{passed} passed, {failed} failed, {len(results)} total\n")

    for rel, status, errors in results:
        icon = "  PASS" if status == "PASS" else "  FAIL"
        print(f"{icon}  {rel}")
        for err in errors:
            print(f"         {err}")

    print("\n" + "=" * 60)

    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
