"""Classify legacy pages into documentation categories.

Uses two signal sources:
- config/taxonomy.yaml: keyword/pattern matching against title and labels
- config/signals.yaml: structural patterns detecting HOW content is written
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from scripts.utils import load_yaml

CONFIG_DIR = Path("config")

# Subcategory routing rules: category -> [(content_pattern, subcategory)]
_SUBCATEGORY_RULES = {
    "runbook": [
        (r"(?mi)(incident|outage|sev[- ]?\d|alert\s+fire)", "incident-response"),
        (r"(?mi)(deploy|release|ship|rollout|canary)", "deployment"),
        (r"(?mi)(troubleshoot|debug|diagnos|error|fix)", "troubleshooting"),
    ],
    "architecture": [
        (r"(?mi)(ADR|decision\s+record|we\s+(chose|decided))", "adrs"),
        (r"(?mi)(service|component|module|domain)\s+(overview|doc|boundar)", "modules"),
    ],
    "product": [
        (r"(?mi)(requirement|user\s+story|acceptance\s+criteria)", "requirements"),
    ],
    "api": [
        (r"(?m)`(GET|POST|PUT|DELETE)\s+/", "endpoints"),
    ],
}


@dataclass
class ClassificationResult:
    category: str
    confidence: float
    signals: list[str] = field(default_factory=list)
    subcategory: str | None = None
    mixed_intents: list[dict] = field(default_factory=list)

    @property
    def is_ambiguous(self) -> bool:
        return self.confidence < 0.5

    @property
    def should_split(self) -> bool:
        return len(self.mixed_intents) > 1


def _load_yaml(path: Path) -> dict:
    return load_yaml(path)


def _score_keywords(
    title: str, content: str, labels: list[str], taxonomy: dict
) -> dict[str, tuple[float, list[str]]]:
    """Score categories by keyword/pattern match from taxonomy.yaml."""
    results: dict[str, tuple[float, list[str]]] = {}
    lower_labels = [lbl.lower() for lbl in labels]

    for cat, rules in taxonomy.get("categories", {}).items():
        score = 0.0
        signals = []

        for kw in rules.get("keywords", []):
            kw_lower = kw.lower()
            if kw_lower in title.lower():
                score += 3.0
                signals.append(f"keyword '{kw}' in title")
            elif kw_lower in lower_labels:
                score += 2.0
                signals.append(f"keyword '{kw}' in labels")
            elif kw_lower in content.lower()[:2000]:
                score += 1.0

        for pattern in rules.get("patterns", []):
            if re.search(pattern, title, re.IGNORECASE):
                score += 5.0
                signals.append(f"title matches '{pattern}'")

        if score > 0:
            results[cat] = (score, signals)

    return results


def _score_structure(content: str, signals_config: dict) -> dict[str, tuple[float, list[str]]]:
    """Score categories by structural patterns from signals.yaml."""
    results: dict[str, tuple[float, list[str]]] = {}

    for cat, signal_list in signals_config.items():
        score = 0.0
        signals = []

        for entry in signal_list:
            matches = re.findall(entry["pattern"], content)
            if matches:
                count = min(len(matches), 3)
                score += entry["weight"] * count
                signals.append(f"{entry['signal']} (x{count})")

        if score > 0:
            results[cat] = (score, signals)

    return results


def _detect_subcategory(category: str, content: str) -> str | None:
    """Route to a specific subdirectory within a category."""
    for pattern, subcat in _SUBCATEGORY_RULES.get(category, []):
        if re.search(pattern, content):
            return subcat
    return None


def _detect_mixed_intents(content: str, signals_config: dict) -> list[dict]:
    """Detect if a page has sections belonging to different categories."""
    # Split by top-level headings
    sections = re.split(r"(?m)^(#{1,2}\s+.+)$", content)
    if len(sections) < 5:  # Need at least 2 headed sections
        return []

    # Pair headings with their content
    category_groups: dict[str, list[str]] = {}
    for i in range(1, len(sections) - 1, 2):
        heading = sections[i].strip()
        body = sections[i + 1] if i + 1 < len(sections) else ""
        if len(body.strip()) < 80:
            continue

        # Classify this section
        section_scores = _score_structure(body, signals_config)
        if section_scores:
            best = max(section_scores, key=lambda k: section_scores[k][0])
            category_groups.setdefault(best, []).append(heading)

    if len(category_groups) < 2:
        return []

    return [
        {"category": cat, "headings": headings}
        for cat, headings in sorted(category_groups.items())
    ]


def classify_page(
    title: str, content: str, labels: list[str], taxonomy: dict
) -> ClassificationResult:
    """Classify a page by merging keyword scores and structural scores.

    Structural signals are weighted 1.5x because they're more reliable
    than keywords for unstructured legacy pages.
    """
    signals_config = _load_yaml(CONFIG_DIR / "signals.yaml")

    kw_scores = _score_keywords(title, content, labels, taxonomy)
    st_scores = _score_structure(content, signals_config)

    # Merge: structural signals weighted 1.5x
    merged: dict[str, tuple[float, list[str]]] = {}
    for cat in set(kw_scores) | set(st_scores):
        kw_s, kw_sig = kw_scores.get(cat, (0.0, []))
        st_s, st_sig = st_scores.get(cat, (0.0, []))
        merged[cat] = (kw_s + st_s * 1.5, kw_sig + st_sig)

    if not merged:
        default = taxonomy.get("default_category", "architecture")
        return ClassificationResult(category=default, confidence=0.0, signals=["no signals"])

    best = max(merged, key=lambda k: merged[k][0])
    best_score, best_signals = merged[best]
    total = sum(s for s, _ in merged.values())

    return ClassificationResult(
        category=best,
        confidence=best_score / total if total > 0 else 0.0,
        signals=best_signals,
        subcategory=_detect_subcategory(best, content),
        mixed_intents=_detect_mixed_intents(content, signals_config),
    )


def load_taxonomy() -> dict:
    return _load_yaml(CONFIG_DIR / "taxonomy.yaml")


def get_target_dir(category: str, taxonomy: dict, subcategory: str | None = None) -> str:
    base = taxonomy.get("categories", {}).get(category, {}).get("target_dir", f"docs/{category}")
    return f"{base}/{subcategory}" if subcategory else base
