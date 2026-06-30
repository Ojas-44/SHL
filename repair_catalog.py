from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

SOURCE_URL = "https://tcp-us-prod-rnd.shl.com/voiceRater/shl-ai-hiring/shl_product_catalog.json"
SOURCE_PATH = Path("catalog_raw.txt")
CATALOG_PATH = Path("catalog.json")
CLEAN_CATALOG_PATH = Path("clean_catalog.json")


def download_catalog(target_path: Path) -> str:
    """Download the catalog if the local copy is missing."""
    with urllib.request.urlopen(SOURCE_URL) as response:
        text = response.read().decode("utf-8")
    target_path.write_text(text, encoding="utf-8")
    return text


def read_catalog_text() -> str:
    """Read the local file when present; otherwise download it."""
    if SOURCE_PATH.exists():
        return SOURCE_PATH.read_text(encoding="utf-8")
    return download_catalog(SOURCE_PATH)


def repair_text_for_json(text: str) -> tuple[str, int, list[int]]:
    """Escape control characters that appear inside JSON strings.

    This is the main repair strategy:
    - walk through the text character by character
    - track whether we are inside a JSON string
    - if a newline, tab, carriage return, or other control character appears
      while inside a string, convert it to a valid JSON escape sequence
    - leave normal JSON structure intact
    """

    result: list[str] = []
    in_string = False
    escaped = False
    repaired_records: list[int] = []

    for char in text:
        if in_string:
            if escaped:
                result.append(char)
                escaped = False
                continue

            if char == "\\":
                result.append(char)
                escaped = True
                continue

            if char == '"':
                result.append(char)
                in_string = False
                continue

            if ord(char) < 32:
                if char == "\n":
                    result.append("\\n")
                elif char == "\r":
                    result.append("\\r")
                elif char == "\t":
                    result.append("\\t")
                elif char == "\b":
                    result.append("\\b")
                elif char == "\f":
                    result.append("\\f")
                else:
                    result.append(f"\\u{ord(char):04x}")
                continue

            result.append(char)
            continue

        if char == '"':
            in_string = True
            result.append(char)
            continue

        result.append(char)

    repaired_text = "".join(result)

    # Count top-level records whose content included control characters inside strings.
    top_level_items = extract_top_level_items(text)
    for index, item in enumerate(top_level_items, start=1):
        if contains_control_char_in_string(item):
            repaired_records.append(index)

    return repaired_text, len(repaired_records), repaired_records


def extract_top_level_items(text: str) -> list[str]:
    """Extract array items at the top level of a JSON array."""
    stripped = text.strip()
    if not stripped:
        return []

    if stripped[0] != "[" or stripped[-1] != "]":
        return []

    items: list[str] = []
    current: list[str] = []
    depth_brackets = 0
    depth_braces = 0
    in_string = False
    escaped = False

    for char in stripped[1:-1]:
        if in_string:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            current.append(char)
            continue

        if char == "[":
            depth_brackets += 1
        elif char == "]":
            depth_brackets = max(0, depth_brackets - 1)
        elif char == "{":
            depth_braces += 1
        elif char == "}":
            depth_braces = max(0, depth_braces - 1)

        if char == "," and depth_brackets == 0 and depth_braces == 0:
            item = "".join(current).strip()
            if item:
                items.append(item)
            current = []
            continue

        current.append(char)

    item = "".join(current).strip()
    if item:
        items.append(item)

    return items


def contains_control_char_in_string(text: str) -> bool:
    """Return True when a control character appears inside a JSON string."""
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                in_string = False
                continue
            if ord(char) < 32:
                return True
            continue

        if char == '"':
            in_string = True

    return False


def build_clean_catalog(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create a smaller, interview-friendly catalog structure."""
    cleaned: list[dict[str, Any]] = []
    for item in data:
        cleaned.append(
            {
                "name": item.get("name", ""),
                "url": item.get("link", ""),
                "description": item.get("description", ""),
                "job_levels": item.get("job_levels", []),
                "keys": item.get("keys", []),
                "duration": item.get("duration", ""),
                "languages": item.get("languages", []),
            }
        )
    return cleaned


def main() -> None:
    raw_text = read_catalog_text()
    repaired_text, repaired_count, repaired_records = repair_text_for_json(raw_text)

    try:
        catalog = json.loads(repaired_text)
        unrepaired_records: list[int] = []
    except json.JSONDecodeError as exc:
        catalog = []
        unrepaired_records = [1]
        print(f"JSON validation still failed: {exc}")

    if isinstance(catalog, list):
        CATALOG_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        clean_catalog = build_clean_catalog(catalog)
        CLEAN_CATALOG_PATH.write_text(json.dumps(clean_catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        raise ValueError("The repaired catalog is not a JSON array.")

    print(f"Total assessments: {len(catalog)}")
    print(f"Repaired records: {repaired_count}")
    print(f"Repaired record indexes: {repaired_records}")
    print(f"Unrepaired records: {unrepaired_records}")
    print(f"Saved repaired catalog to {CATALOG_PATH}")
    print(f"Saved cleaned catalog to {CLEAN_CATALOG_PATH}")


if __name__ == "__main__":
    main()
