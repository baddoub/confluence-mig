Analyze fetched legacy pages to discover what's actually there before restructuring.

Run `python scripts/discover.py` to scan all pages in `raw/current/` and produce a discovery report.

**The report shows:**
- Category distribution (how many pages match each taxonomy category)
- Empty categories (defined but no content matched — consider removing)
- Ambiguous pages (low confidence — need manual review before placement)
- Mixed-intent pages (candidates for splitting into separate docs)
- Top classification signals (what patterns are driving decisions)
- Recommendations (dominant categories, taxonomy gaps)

**After reviewing the report:**
1. Adjust `config/taxonomy.yaml` keywords or `config/signals.yaml` patterns if categories are wrong
2. Remove empty categories or add missing ones
3. Then run `/restructure` with confidence the taxonomy fits the actual content
