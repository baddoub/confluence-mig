"""Discover: analyze fetched legacy pages and report what's actually there.

Scans all pages in raw/current/, classifies each one, and produces a
discovery report showing content distribution, taxonomy gaps, and
recommendations before restructuring.
"""

import json
from collections import defaultdict
from pathlib import Path

from scripts.convert import html_to_markdown
from scripts.taxonomy import classify_page, load_taxonomy

RAW_DIR = Path("raw/current")
RAW_DIR_FALLBACK = Path("raw")


def _load_pages() -> list[dict]:
    """Load all fetched pages with their HTML content and metadata."""
    source_dir = RAW_DIR if RAW_DIR.exists() else RAW_DIR_FALLBACK
    pages = []

    for meta_path in sorted(source_dir.glob("*.meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        html_path = meta_path.with_suffix("").with_suffix(".html")
        html = html_path.read_text(encoding="utf-8") if html_path.exists() else ""
        meta["_html"] = html
        pages.append(meta)

    return pages


def discover() -> dict:
    """Analyze all fetched pages and return a structured discovery report."""
    pages = _load_pages()
    if not pages:
        return {"error": "No pages found in raw/current/ or raw/. Run /fetch first."}

    taxonomy = load_taxonomy()
    defined_categories = set(taxonomy.get("categories", {}).keys())

    # Classify every page
    results = []
    for page in pages:
        content = html_to_markdown(page.get("_html", ""))
        labels = [lbl.get("name", lbl) if isinstance(lbl, dict) else lbl
                  for lbl in page.get("labels", [])]
        classification = classify_page(
            title=page.get("title", ""),
            content=content,
            labels=labels,
            taxonomy=taxonomy,
        )
        results.append({
            "id": page.get("id"),
            "title": page.get("title", "untitled"),
            "category": classification.category,
            "subcategory": classification.subcategory,
            "confidence": round(classification.confidence, 2),
            "signals": classification.signals,
            "is_ambiguous": classification.is_ambiguous,
            "should_split": classification.should_split,
            "mixed_intents": classification.mixed_intents,
        })

    # --- Build report ---
    report: dict = {"total_pages": len(results)}

    # 1. Distribution by category
    by_category: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_category[r["category"]].append(r)

    report["distribution"] = {
        cat: {
            "count": len(items),
            "percent": round(100 * len(items) / len(results)),
            "avg_confidence": round(
                sum(i["confidence"] for i in items) / len(items), 2
            ),
        }
        for cat, items in sorted(by_category.items(), key=lambda x: -len(x[1]))
    }

    # 2. Empty categories (defined in taxonomy but no pages matched)
    matched_categories = set(by_category.keys())
    report["empty_categories"] = sorted(defined_categories - matched_categories)

    # 3. Unexpected categories (matched but not in taxonomy — shouldn't happen,
    #    but flags misconfiguration)
    report["unexpected_categories"] = sorted(matched_categories - defined_categories)

    # 4. Ambiguous pages (low confidence — need manual review)
    ambiguous = [r for r in results if r["is_ambiguous"]]
    report["ambiguous"] = {
        "count": len(ambiguous),
        "pages": [
            {"title": r["title"], "category": r["category"],
             "confidence": r["confidence"], "signals": r["signals"]}
            for r in sorted(ambiguous, key=lambda x: x["confidence"])
        ],
    }

    # 5. Mixed-intent pages (candidates for splitting)
    mixed = [r for r in results if r["should_split"]]
    report["mixed_intent"] = {
        "count": len(mixed),
        "pages": [
            {"title": r["title"], "intents": r["mixed_intents"]}
            for r in mixed
        ],
    }

    # 6. Subcategory distribution
    sub_dist: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in results:
        if r["subcategory"]:
            sub_dist[r["category"]][r["subcategory"]] += 1
    report["subcategories"] = {
        cat: dict(subs) for cat, subs in sorted(sub_dist.items())
    }

    # 7. Top signals (most common classification signals across all pages)
    signal_counts: dict[str, int] = defaultdict(int)
    for r in results:
        for s in r["signals"]:
            signal_counts[s] += 1
    report["top_signals"] = dict(
        sorted(signal_counts.items(), key=lambda x: -x[1])[:15]
    )

    # 8. All pages with classifications (for detailed review)
    report["pages"] = [
        {k: v for k, v in r.items() if k not in ("mixed_intents",)}
        for r in sorted(results, key=lambda x: (x["category"], -x["confidence"]))
    ]

    return report


def print_report(report: dict):
    """Pretty-print the discovery report to stdout."""
    if "error" in report:
        print(report["error"])
        return

    print("=" * 60)
    print("DISCOVERY REPORT")
    print("=" * 60)
    print(f"\nTotal pages analyzed: {report['total_pages']}")

    # Distribution
    print("\n--- Category Distribution ---")
    for cat, info in report["distribution"].items():
        bar = "#" * (info["percent"] // 2)
        print(f"  {cat:20s} {info['count']:3d} ({info['percent']:2d}%) "
              f"avg conf: {info['avg_confidence']:.2f}  {bar}")

    # Empty categories
    if report["empty_categories"]:
        print("\n--- Empty Categories (no matching pages) ---")
        for cat in report["empty_categories"]:
            print(f"  {cat} — consider removing from taxonomy or adding content")

    # Ambiguous
    amb = report["ambiguous"]
    if amb["count"]:
        print(f"\n--- Ambiguous Pages ({amb['count']}) — need manual review ---")
        for p in amb["pages"]:
            print(f"  [{p['confidence']:.2f}] {p['title']}")
            for s in p["signals"][:3]:
                print(f"         -> {s}")

    # Mixed intent
    mix = report["mixed_intent"]
    if mix["count"]:
        print(f"\n--- Mixed-Intent Pages ({mix['count']}) — candidates for splitting ---")
        for p in mix["pages"]:
            cats = ", ".join(f"{i['category']}({len(i['headings'])})" for i in p["intents"])
            print(f"  {p['title']}: {cats}")

    # Subcategories
    if report["subcategories"]:
        print("\n--- Subcategory Breakdown ---")
        for cat, subs in report["subcategories"].items():
            for sub, count in subs.items():
                print(f"  {cat}/{sub}: {count}")

    # Top signals
    print("\n--- Most Common Signals ---")
    for sig, count in report["top_signals"].items():
        print(f"  {count:3d}x  {sig}")

    # Recommendations
    print("\n--- Recommendations ---")
    dist = report["distribution"]
    total = report["total_pages"]

    # Dominant category warning
    for cat, info in dist.items():
        if info["percent"] > 50:
            print(f"  ! '{cat}' has {info['percent']}% of pages — "
                  "consider splitting into subcategories")

    # Low confidence warning
    if amb["count"] > total * 0.2:
        print(f"  ! {amb['count']}/{total} pages are ambiguous — "
              "review taxonomy rules or signals")

    if report["empty_categories"]:
        print(f"  ! {len(report['empty_categories'])} categories have no content — "
              "remove or add content")

    if not report["empty_categories"] and amb["count"] == 0:
        print("  All categories populated, no ambiguous pages. Ready to /restructure.")

    print("\n" + "=" * 60)


def main():
    report = discover()
    print_report(report)

    # Also save full report as JSON for programmatic use
    out = Path("raw/discovery_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    # Remove non-serializable items
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nFull report saved to {out}")


if __name__ == "__main__":
    main()
