"""
catalog_loader.py
------------------
Responsible for reading catalog.json and turning each raw entry into a
clean, predictable Python dictionary that the rest of the app can rely on.
"""

import json
import os
from typing import Any, Dict, List


def load_raw_catalog(path: str = "catalog.json") -> List[Dict[str, Any]]:
    """Read catalog.json from disk and return the underlying list of items."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Could not find '{path}'. Make sure catalog.json sits next to app.py."
        )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        for key in ("assessments", "catalog", "items", "data"):
            if key in data and isinstance(data[key], list):
                return data[key]
        for value in data.values():
            if isinstance(value, list):
                return value
        raise ValueError("catalog.json is a dict but no list of items was found inside it.")

    if isinstance(data, list):
        return data

    raise ValueError("catalog.json must contain either a list or a dict wrapping a list.")


def _as_text(value: Any) -> str:
    """Normalize list/string values into a readable, comma-separated string."""
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v is not None)
    return str(value)


def parse_entry(raw: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Convert one raw catalog entry into a consistent dictionary."""
    name = raw.get("name") or raw.get("title") or f"Untitled Assessment {index}"
    url = raw.get("url") or raw.get("link") or ""
    description = raw.get("description") or raw.get("summary") or ""
    test_type = _as_text(
        raw.get("test_type")
        or raw.get("category")
        or raw.get("keys")
        or raw.get("test_categories")
        or raw.get("type")
    )
    job_levels = _as_text(raw.get("job_levels") or raw.get("level"))
    keys = _as_text(raw.get("keys") or raw.get("categories") or raw.get("test_categories"))
    duration = raw.get("duration_minutes") or raw.get("duration") or ""
    remote_testing = bool(raw.get("remote_testing", False))
    adaptive_irt = bool(raw.get("adaptive_irt", False))

    return {
        "id": index,
        "name": name,
        "url": url,
        "description": description,
        "test_type": test_type,
        "job_levels": job_levels,
        "keys": keys,
        "duration_minutes": duration,
        "remote_testing": remote_testing,
        "adaptive_irt": adaptive_irt,
    }


def build_search_text(entry: Dict[str, Any]) -> str:
    """Build a single search-friendly text string from catalog metadata."""
    parts = [
        entry["name"],
        entry["description"],
        f"Test type: {entry['test_type']}" if entry["test_type"] else "",
        f"Job levels: {entry['job_levels']}" if entry["job_levels"] else "",
        f"Keys: {entry['keys']}" if entry["keys"] else "",
    ]
    return " | ".join(p for p in parts if p)


def load_and_parse_catalog(path: str = "catalog.json") -> List[Dict[str, Any]]:
    """Load and parse the catalog in one step."""
    raw_entries = load_raw_catalog(path)
    return [parse_entry(raw, i) for i, raw in enumerate(raw_entries)]


if __name__ == "__main__":
    entries = load_and_parse_catalog("catalog.json")
    print(f"Loaded {len(entries)} entries.\n")
    for entry in entries[:2]:
        print(entry)
        print("Search text:", build_search_text(entry))
        print()
