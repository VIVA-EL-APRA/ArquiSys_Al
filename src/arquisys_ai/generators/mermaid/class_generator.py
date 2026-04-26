from __future__ import annotations

import re

from arquisys_ai.core.models import AnalystResult
from arquisys_ai.utils.text import to_identifier


def _parse_class_entry(entry: str) -> tuple[str, list[str]]:
    match = re.match(r"\s*([^(]+?)\s*(?:\(([^)]*)\))?\s*$", entry)
    if not match:
        return entry.strip(), []

    class_name = match.group(1).strip()
    attrs_raw = match.group(2)
    if not attrs_raw:
        return class_name, []

    attrs = [attr.strip() for attr in attrs_raw.split(",") if attr.strip()]
    return class_name, attrs


def _unique_identifier(raw_name: str, idx: int, used_ids: set[str]) -> str:
    base = to_identifier(raw_name, fallback_prefix=f"Class{idx}")
    candidate = base
    suffix = 2

    while candidate in used_ids:
        candidate = f"{base}{suffix}"
        suffix += 1

    used_ids.add(candidate)
    return candidate


def generate_class_mermaid(analysis: AnalystResult) -> str:
    class_entries = analysis.classes or ["Sistema"]
    parsed = [_parse_class_entry(entry) for entry in class_entries]

    lines: list[str] = ["classDiagram"]
    class_ids: list[str] = []
    used_ids: set[str] = set()

    for idx, (class_name, attrs) in enumerate(parsed, start=1):
        class_id = _unique_identifier(class_name, idx, used_ids)
        class_ids.append(class_id)

        if attrs:
            lines.append(f"    class {class_id} {{")
            for attr in attrs:
                attr_name = to_identifier(attr, fallback_prefix="field")
                lines.append(f"        +{attr_name[:1].lower() + attr_name[1:]} string")
            lines.append("    }")
        else:
            lines.append(f"    class {class_id}")

    if len(class_ids) >= 2:
        lines.append(f"    {class_ids[0]} --> {class_ids[1]} : relacion")

    return "\n".join(lines)
