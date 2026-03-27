"""Classify unstructured legacy pages into documentation categories.

Uses three layers of analysis:
1. Keyword/pattern matching from config/taxonomy.yaml
2. Structural intent detection (analyzes HOW the page is written)
3. Content-section analysis (detects mixed-intent pages that should be split)
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

TAXONOMY_PATH = Path("config/taxonomy.yaml")


@dataclass
class ClassificationResult:
    """Result of classifying a single page."""

    category: str
    confidence: float
    signals: list[str] = field(default_factory=list)
    suggested_subcategory: str | None = None
    # If the page covers multiple topics, list them for potential splitting
    mixed_intents: list[dict] = field(default_factory=list)

    @property
    def is_ambiguous(self) -> bool:
        return self.confidence < 0.5

    @property
    def should_split(self) -> bool:
        return len(self.mixed_intents) > 1


def load_taxonomy() -> dict:
    with open(TAXONOMY_PATH) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Layer 1: Keyword & pattern matching (from taxonomy.yaml)
# ---------------------------------------------------------------------------

def _score_keywords(
    title: str, content: str, labels: list[str], taxonomy: dict
) -> dict[str, tuple[float, list[str]]]:
    """Score each category by keyword/pattern match. Returns {category: (score, signals)}."""
    categories = taxonomy.get("categories", {})
    results: dict[str, tuple[float, list[str]]] = {}

    for category, rules in categories.items():
        score = 0.0
        signals = []

        for keyword in rules.get("keywords", []):
            kw_lower = keyword.lower()
            if kw_lower in title.lower():
                score += 3.0
                signals.append(f"keyword '{keyword}' in title")
            if kw_lower in [lbl.lower() for lbl in labels]:
                score += 2.0
                signals.append(f"keyword '{keyword}' in labels")
            # Search deeper into content, not just first 500 chars
            if kw_lower in content.lower()[:2000]:
                score += 1.0
                signals.append(f"keyword '{keyword}' in content")

        for pattern in rules.get("patterns", []):
            if re.search(pattern, title, re.IGNORECASE):
                score += 5.0
                signals.append(f"title matches pattern '{pattern}'")

        if score > 0:
            results[category] = (score, signals)

    return results


# ---------------------------------------------------------------------------
# Layer 2: Structural intent detection
# ---------------------------------------------------------------------------
# Detects the PURPOSE of a page by analyzing structural patterns in its
# content, independent of specific keywords. This is what catches pages
# with vague titles like "Notes", "Process", or "Team Stuff".

_STRUCTURAL_SIGNALS: list[tuple[str, str, str, float]] = [
    # (pattern, description, category, weight)

    # --- Runbook signals: step-by-step procedures ---
    # Prerequisites + Steps + Rollback together are the strongest runbook signal.
    # All heading patterns use (?mi) for case-insensitive + multiline.
    (r"(?mi)^#{1,3}\s*step\s*\d", "numbered step headings", "runbook", 5.0),
    (r"(?mi)^#{1,3}\s*prerequisites?\b", "prerequisites section", "runbook", 5.0),
    (r"(?mi)^#{1,3}\s*rollback\b", "rollback section", "runbook", 6.0),
    (r"(?mi)^#{1,3}\s*escalat", "escalation section", "runbook", 3.5),
    (r"(?mi)^#{1,3}\s*(troubleshoot|common\s+(issues?|errors?|problems?))", "troubleshooting section", "runbook", 4.0),
    (r"(?mi)(sudo|ssh|kubectl|docker run|systemctl|aws\s|gcloud)\s", "CLI/ops commands", "runbook", 2.5),
    (r"(?m)^(1\.\s+.+\n){3,}", "numbered procedure steps", "runbook", 3.0),
    (r"(?mi)(if\s+this\s+fails|when\s+the\s+alert\s+fires|in\s+case\s+of)", "conditional ops language", "runbook", 3.0),
    (r"(?mi)(on[- ]?call|pager|incident\s+commander|severity\s+[0-9p])", "incident response terms", "runbook", 3.5),
    # Procedural combo: prerequisites or steps heading + rollback heading in
    # same doc is a very strong "this is a runbook" signal.
    (r"(?msi)^#{1,3}\s*(steps?|prerequisites).*?^#{1,3}\s*rollback", "procedure with rollback pattern", "runbook", 6.0),

    # --- Architecture signals: system design language ---
    (r"(?mi)^#{1,3}\s*(system\s+)?overview\b", "overview heading", "architecture", 1.5),
    (r"(?mi)(→|->|<->|communicates?\s+with|calls?|depends?\s+on|upstream|downstream)", "dependency language", "architecture", 2.0),
    (r"(?mi)(service|component|module|layer|tier)\s+(diagram|overview|architecture)", "architecture terms", "architecture", 3.0),
    (r"(?mi)(trade-?off|we\s+chose|we\s+decided|alternative|option\s+\d|pro\s*\/\s*con)", "decision language", "architecture", 3.0),
    (r"(?mi)^#{1,3}\s*(context|decision|consequences|status)\s*$", "ADR section headings", "architecture", 4.0),
    (r"(?mi)(data\s*flow|sequence\s*diagram|class\s*diagram|er\s*diagram|c4\s*model)", "diagram references", "architecture", 2.5),
    (r"(?mi)(accepted|proposed|deprecated|superseded)\s*$", "ADR status values", "architecture", 3.0),

    # --- API signals: endpoint documentation ---
    (r"(?m)`(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+/", "HTTP method + path", "api", 5.0),
    (r"(?mi)(request\s+body|response\s+body|query\s+param|path\s+param|header)", "API param sections", "api", 3.0),
    (r"(?m)(2[0-9]{2}|4[0-9]{2}|5[0-9]{2})\s+(OK|Created|Bad Request|Not Found|Unauthorized|Internal)", "HTTP status codes", "api", 3.5),
    (r"(?mi)(bearer\s+token|api[- ]?key|oauth|jwt|authorization\s+header)", "auth mechanism", "api", 2.5),
    (r"(?mi)(swagger|openapi|endpoint|rate[- ]?limit)", "API doc terms", "api", 2.0),
    (r'(?m)"(application|content)[/-]json"', "JSON content types", "api", 2.0),
    (r"(?m)```json\s*\n\s*\{", "JSON code blocks", "api", 1.5),

    # --- Onboarding signals: setup and getting-started ---
    (r"(?mi)^#{1,3}\s*(getting\s+started|quick\s*start|first\s+steps?)", "getting started heading", "onboarding", 4.0),
    (r"(?mi)(clone\s+the\s+repo|git\s+clone|fork\s+(the|this))", "repo clone instructions", "onboarding", 3.5),
    (r"(?mi)(install\s+(dependencies|requirements|packages)|pip\s+install|npm\s+install|brew\s+install)", "dependency install", "onboarding", 3.0),
    (r"(?mi)(local\s+(development|setup|env)|dev\s+environment)", "local dev setup", "onboarding", 3.5),
    (r"(?mi)(new\s+(developer|hire|team\s+member|joiner)|first\s+(day|week))", "new hire language", "onboarding", 4.0),
    (r"(?mi)(PR\s+(process|workflow|review)|branch(ing)?\s+(strategy|model|convention))", "dev workflow terms", "onboarding", 2.5),
    (r"(?mi)(coding\s+(standards?|conventions?|style)|linting|formatter)", "coding standards", "onboarding", 2.5),

    # --- Infrastructure signals: cloud/ops platform ---
    # These describe WHAT the platform is, not HOW to operate it (that's runbook).
    # Weighted lower than runbook structural signals to avoid stealing procedural pages.
    (r"(?mi)(vpc|subnet|security\s+group|load\s+balancer|auto[- ]?scaling|cdn)", "cloud networking terms", "infrastructure", 3.0),
    (r"(?mi)(terraform|cloudformation|pulumi|ansible|helm\s+chart)", "IaC tools", "infrastructure", 3.5),
    (r"(?mi)(ci/?cd|pipeline|github\s+actions?|jenkins|circle\s*ci|gitlab\s+ci|buildkite)", "CI/CD terms", "infrastructure", 3.0),
    (r"(?mi)(prometheus|grafana|datadog|cloudwatch|new\s*relic|pagerduty|opsgenie)", "monitoring tools", "infrastructure", 2.5),
    (r"(?mi)(s3|rds|ec2|ecs|eks|lambda|dynamodb|sqs|sns|kinesis)", "AWS services", "infrastructure", 2.0),
    (r"(?mi)(gke|cloud\s+run|bigquery|cloud\s+sql|pub/?sub)", "GCP services", "infrastructure", 2.0),
    (r"(?mi)(dockerfile|docker[- ]?compose|k8s|kubernetes|pod|deployment|ingress)", "container/k8s terms", "infrastructure", 2.0),
    # Strong infra signal: describing topology/architecture of the platform itself
    (r"(?mi)^#{1,3}\s*(infrastructure|cloud\s+architecture|platform\s+overview)", "infra section headings", "infrastructure", 4.0),
    (r"(?mi)(\d+\s+(cluster|node|instance|replica|region)s?\b)", "infra scale/topology", "infrastructure", 3.0),

    # --- Product signals: requirements and features ---
    (r"(?mi)^#{1,3}\s*(user\s+stor(y|ies)|acceptance\s+criteria)", "requirement sections", "product", 5.0),
    (r"(?mi)(as\s+a\s+.{3,30},?\s+I\s+want)", "user story format", "product", 5.0),
    (r"(?mi)(given\s+.{3,40}\s+when\s+.{3,40}\s+then)", "BDD scenario format", "product", 4.0),
    (r"(?mi)(MVP|minimum\s+viable|feature\s+flag|release\s+plan|roadmap)", "product planning terms", "product", 3.0),
    (r"(?mi)(stakeholder|customer\s+(need|feedback|request)|business\s+requirement)", "stakeholder language", "product", 3.0),
    (r"(?mi)(in[- ]scope|out[- ]of[- ]scope|scope)", "scope sections", "product", 2.0),
    (r"(?mi)(priority|must[- ]have|should[- ]have|could[- ]have|won'?t[- ]have|MoSCoW)", "prioritization language", "product", 3.0),
]


def _score_structure(content: str) -> dict[str, tuple[float, list[str]]]:
    """Detect page intent by analyzing structural patterns in the content."""
    results: dict[str, tuple[float, list[str]]] = {}

    for pattern, description, category, weight in _STRUCTURAL_SIGNALS:
        matches = re.findall(pattern, content)
        if matches:
            match_count = min(len(matches), 3)  # Cap at 3 to avoid runaway scoring
            score = weight * match_count
            if category not in results:
                results[category] = (0.0, [])
            existing_score, existing_signals = results[category]
            results[category] = (
                existing_score + score,
                existing_signals + [f"{description} (x{match_count})"],
            )

    return results


# ---------------------------------------------------------------------------
# Layer 3: Content-section analysis (detect mixed-intent pages)
# ---------------------------------------------------------------------------

def _detect_sections(content: str) -> list[dict]:
    """Split content by headings and classify each section independently.

    Returns a list of {heading, category, confidence, start_line, end_line}
    for pages that contain multiple distinct intents.
    """
    lines = content.split("\n")
    sections: list[dict] = []
    current_heading = "(intro)"
    current_start = 0
    current_lines: list[str] = []

    for i, line in enumerate(lines):
        heading_match = re.match(r"^(#{1,3})\s+(.+)", line)
        if heading_match and current_lines:
            # Close previous section
            section_text = "\n".join(current_lines)
            if len(section_text.strip()) > 50:  # Skip tiny sections
                sections.append({
                    "heading": current_heading,
                    "text": section_text,
                    "start_line": current_start,
                    "end_line": i - 1,
                })
            current_heading = heading_match.group(2).strip()
            current_start = i
            current_lines = []
        else:
            current_lines.append(line)

    # Close final section
    if current_lines:
        section_text = "\n".join(current_lines)
        if len(section_text.strip()) > 50:
            sections.append({
                "heading": current_heading,
                "text": section_text,
                "start_line": current_start,
                "end_line": len(lines) - 1,
            })

    # Classify each section
    for section in sections:
        struct_scores = _score_structure(section["text"])
        if struct_scores:
            best = max(struct_scores, key=lambda k: struct_scores[k][0])
            score, signals = struct_scores[best]
            section["category"] = best
            section["confidence"] = min(score / 10.0, 1.0)
            section["signals"] = signals
        else:
            section["category"] = None
            section["confidence"] = 0.0
            section["signals"] = []

    return sections


def _detect_mixed_intents(content: str) -> list[dict]:
    """Detect if a page covers multiple distinct topics that should be split."""
    sections = _detect_sections(content)

    # Group sections by detected category
    category_groups: dict[str, list[dict]] = {}
    for section in sections:
        cat = section.get("category")
        if cat:
            category_groups.setdefault(cat, []).append(section)

    # Only flag as mixed if there are 2+ categories with meaningful content
    meaningful = {
        cat: secs for cat, secs in category_groups.items()
        if sum(len(s["text"]) for s in secs) > 100
    }

    if len(meaningful) <= 1:
        return []

    mixed = []
    for cat, secs in meaningful.items():
        headings = [s["heading"] for s in secs]
        total_len = sum(len(s["text"]) for s in secs)
        mixed.append({
            "category": cat,
            "headings": headings,
            "char_count": total_len,
            "sections": secs,
        })

    return sorted(mixed, key=lambda m: m["char_count"], reverse=True)


# ---------------------------------------------------------------------------
# Layer 4: Subcategory detection
# ---------------------------------------------------------------------------

def _detect_subcategory(category: str, title: str, content: str) -> str | None:
    """Detect specific subcategory for routing within a category's directory."""
    if category == "runbook":
        if re.search(r"(?mi)(incident|outage|sev[- ]?\d|page|alert\s+fire)", content):
            return "incident-response"
        if re.search(r"(?mi)(deploy|release|ship|rollout|canary|blue[- ]?green)", content):
            return "deployment"
        if re.search(r"(?mi)(troubleshoot|debug|diagnos|error|fix|resolv)", content):
            return "troubleshooting"

    if category == "architecture":
        if re.search(r"(?mi)(ADR|decision\s+record|we\s+(chose|decided))", content):
            return "adrs"
        if re.search(r"(?mi)(service\s+(overview|doc)|component|microservice)", content):
            return "services"

    if category == "product":
        if re.search(r"(?mi)(requirement|user\s+story|acceptance\s+criteria|feature\s+spec)", content):
            return "requirements"

    if category == "api":
        if re.search(r"(?m)`(GET|POST|PUT|DELETE)\s+/", content):
            return "endpoints"

    return None


# ---------------------------------------------------------------------------
# Main classifier
# ---------------------------------------------------------------------------

def classify_page(
    title: str, content: str, labels: list[str], taxonomy: dict
) -> ClassificationResult:
    """Classify a page using all three layers of analysis.

    For unstructured legacy pages, structural analysis often outweighs
    keyword matching — a page titled "Notes" that contains numbered steps,
    rollback instructions, and CLI commands is a runbook.
    """
    # Layer 1: keyword/pattern scores
    kw_scores = _score_keywords(title, content, labels, taxonomy)

    # Layer 2: structural intent scores (weighted 1.5x — structural evidence
    # is more reliable than keywords for unstructured pages)
    struct_scores = _score_structure(content)

    # Merge scores
    all_categories: set[str] = set(kw_scores.keys()) | set(struct_scores.keys())
    merged: dict[str, tuple[float, list[str]]] = {}

    for cat in all_categories:
        kw_score, kw_signals = kw_scores.get(cat, (0.0, []))
        st_score, st_signals = struct_scores.get(cat, (0.0, []))
        merged[cat] = (kw_score + st_score * 1.5, kw_signals + st_signals)

    # Pick winner
    if not merged:
        default = taxonomy.get("default_category", "architecture")
        return ClassificationResult(
            category=default,
            confidence=0.0,
            signals=["no signals detected — defaulting"],
        )

    best = max(merged, key=lambda k: merged[k][0])
    best_score, best_signals = merged[best]
    total = sum(s for s, _ in merged.values())
    confidence = best_score / total if total > 0 else 0.0

    # Layer 3: detect mixed intents
    mixed = _detect_mixed_intents(content)

    # Layer 4: subcategory
    subcategory = _detect_subcategory(best, title, content)

    return ClassificationResult(
        category=best,
        confidence=confidence,
        signals=best_signals,
        suggested_subcategory=subcategory,
        mixed_intents=mixed,
    )


def get_target_dir(category: str, taxonomy: dict, subcategory: str | None = None) -> str:
    """Get the target directory for a category, optionally with subcategory."""
    categories = taxonomy.get("categories", {})
    base = categories.get(category, {}).get("target_dir", f"docs/{category}")
    if subcategory:
        return f"{base}/{subcategory}"
    return base
