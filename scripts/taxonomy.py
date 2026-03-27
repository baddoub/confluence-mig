"""Classify pages into documentation categories using taxonomy rules."""

import re
from pathlib import Path

import yaml

TAXONOMY_PATH = Path("config/taxonomy.yaml")


def load_taxonomy() -> dict:
    with open(TAXONOMY_PATH) as f:
        return yaml.safe_load(f)


def classify_page(title: str, content: str, labels: list[str], taxonomy: dict) -> tuple[str, float]:
    """Classify a page into a category based on taxonomy rules.

    Returns (category, confidence) where confidence is 0.0 to 1.0.
    """
    categories = taxonomy.get("categories", {})
    scores: dict[str, float] = {}

    for category, rules in categories.items():
        score = 0.0

        # Keyword matching (weighted by where they appear)
        for keyword in rules.get("keywords", []):
            kw_lower = keyword.lower()
            if kw_lower in title.lower():
                score += 3.0  # Strong signal: keyword in title
            if kw_lower in labels:
                score += 2.0  # Medium signal: keyword in labels
            if kw_lower in content.lower()[:500]:
                score += 1.0  # Weak signal: keyword in content intro

        # Pattern matching against title
        for pattern in rules.get("patterns", []):
            if re.search(pattern, title, re.IGNORECASE):
                score += 5.0  # Very strong signal: pattern match on title

        if score > 0:
            scores[category] = score

    if not scores:
        default = taxonomy.get("default_category", "architecture")
        return default, 0.0

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = scores[best] / total if total > 0 else 0.0

    return best, confidence


def get_target_dir(category: str, taxonomy: dict) -> str:
    """Get the target directory for a category."""
    categories = taxonomy.get("categories", {})
    if category in categories:
        return categories[category].get("target_dir", f"docs/{category}")
    return taxonomy.get("default_target_dir", "docs/architecture")
