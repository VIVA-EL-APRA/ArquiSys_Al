from __future__ import annotations

from arquisys_ai.utils.text import normalize_text, to_identifier


def dedupe(items: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for item in items:
        clean = item.strip()
        if not clean:
            continue
        key = normalize_text(clean)
        if key in seen:
            continue
        seen.add(key)
        unique.append(clean)
    return unique


def quote_label(text: str) -> str:
    return text.replace('"', "'").strip() or "Item"


def make_unique_id(raw_name: str, fallback_prefix: str, used_ids: set[str]) -> str:
    base = to_identifier(raw_name, fallback_prefix=fallback_prefix)
    candidate = base
    suffix = 2
    while candidate in used_ids:
        candidate = f"{base}{suffix}"
        suffix += 1
    used_ids.add(candidate)
    return candidate
