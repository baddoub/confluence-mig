"""Convert fetched Confluence HTML (storage format) to Markdown."""

import argparse
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify as md

RAW_DIR = Path("raw/current")
RAW_DIR_FALLBACK = Path("raw")
OUTPUT_DIR = Path("converted")


def clean_confluence_html(html: str) -> str:
    """Pre-process Confluence storage format before markdown conversion."""
    soup = BeautifulSoup(html, "html.parser")

    # Convert Confluence macros to readable content
    for macro in soup.find_all("ac:structured-macro"):
        macro_name = macro.get("ac:name", "")

        if macro_name == "code":
            # Convert code macro to <pre><code>
            body = macro.find("ac:plain-text-body")
            if body:
                lang_param = macro.find("ac:parameter", {"ac:name": "language"})
                lang = lang_param.get_text() if lang_param else ""
                pre = soup.new_tag("pre")
                code = soup.new_tag("code", attrs={"class": f"language-{lang}"} if lang else {})
                code.string = body.get_text()
                pre.append(code)
                macro.replace_with(pre)

        elif macro_name in ("info", "note", "warning", "tip"):
            # Convert info/note/warning panels to blockquotes
            body = macro.find("ac:rich-text-body")
            if body:
                bq = soup.new_tag("blockquote")
                prefix = soup.new_tag("strong")
                prefix.string = f"{macro_name.upper()}: "
                bq.append(prefix)
                for child in list(body.children):
                    bq.append(child)
                macro.replace_with(bq)

        elif macro_name == "expand":
            # Convert expand macro to details/summary
            title_param = macro.find("ac:parameter", {"ac:name": "title"})
            body = macro.find("ac:rich-text-body")
            if body:
                details = soup.new_tag("details")
                summary = soup.new_tag("summary")
                summary.string = title_param.get_text() if title_param else "Details"
                details.append(summary)
                for child in list(body.children):
                    details.append(child)
                macro.replace_with(details)

        elif macro_name == "toc":
            # Remove table of contents macro (markdown readers generate their own)
            macro.decompose()

    # Convert Confluence user mentions
    for mention in soup.find_all("ri:user"):
        account_id = mention.get("ri:account-id", "unknown")
        mention.replace_with(f"@user({account_id})")

    # Convert Confluence links
    for link in soup.find_all("ac:link"):
        page_ref = link.find("ri:page")
        if page_ref:
            page_title = page_ref.get("ri:content-title", "unknown")
            link_body = link.find("ac:link-body") or link.find("ac:plain-text-link-body")
            display = link_body.get_text() if link_body else page_title
            a_tag = soup.new_tag("a", href=f"confluence://{page_title}")
            a_tag.string = display
            link.replace_with(a_tag)

    return str(soup)


def html_to_markdown(html: str) -> str:
    """Convert cleaned HTML to markdown."""
    cleaned = clean_confluence_html(html)
    markdown = md(cleaned, heading_style="ATX", bullets="-", strip=["img"])
    # Clean up excessive blank lines
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


def convert_file(html_path: Path) -> tuple[str, dict]:
    """Convert a single HTML file and return (markdown, metadata)."""
    html = html_path.read_text(encoding="utf-8")
    meta_path = html_path.with_suffix(".meta.json")
    meta = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    markdown = html_to_markdown(html)
    return markdown, meta


def main():
    parser = argparse.ArgumentParser(description="Convert fetched HTML to Markdown")
    parser.add_argument("--output-dir", default="converted", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Prefer raw/current/ (snapshot-based), fall back to raw/ (legacy layout)
    source_dir = RAW_DIR if RAW_DIR.exists() else RAW_DIR_FALLBACK
    html_files = sorted(source_dir.glob("*.html"))
    if not html_files:
        print("No HTML files found in raw/current/ or raw/. Run fetch_space.py first.")
        return

    converted = 0
    for html_path in html_files:
        markdown, meta = convert_file(html_path)
        title = meta.get("title", html_path.stem)
        slug = meta.get("slug", html_path.stem)

        out_path = output_dir / f"{slug}.md"
        out_path.write_text(markdown, encoding="utf-8")
        converted += 1
        print(f"  Converted: {title} -> {out_path}")

    print(f"\nConverted {converted} files to {output_dir}/")


if __name__ == "__main__":
    main()
