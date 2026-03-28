"""Shared utilities used across migration scripts."""

import os
import re
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


def slugify(title: str, max_len: int = 80) -> str:
    """Convert a page title to a filesystem-safe kebab-case slug."""
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug.strip("-")[:max_len]


def load_yaml(path: str | Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _expand_env_vars(obj):
    """Recursively expand ${VAR} placeholders in strings from environment."""
    if isinstance(obj, str):
        return re.sub(
            r"\$\{(\w+)\}",
            lambda m: os.environ.get(m.group(1), m.group(0)),
            obj,
        )
    if isinstance(obj, dict):
        return {k: _expand_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env_vars(item) for item in obj]
    return obj


def load_space_config() -> dict:
    config = load_yaml("config/spaces.yaml")
    return _expand_env_vars(config)


def parse_frontmatter(filepath: Path) -> tuple[dict, str]:
    """Parse YAML frontmatter and body from a markdown file."""
    text = filepath.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    return yaml.safe_load(parts[1]) or {}, parts[2].strip()


def update_frontmatter(filepath: Path, updates: dict):
    """Update specific frontmatter fields in a file."""
    meta, body = parse_frontmatter(filepath)
    meta.update(updates)
    frontmatter = yaml.dump(meta, default_flow_style=False, sort_keys=False).strip()
    filepath.write_text(f"---\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8")
