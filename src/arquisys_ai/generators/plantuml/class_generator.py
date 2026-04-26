from __future__ import annotations

import re

from arquisys_ai.core.models import AnalystResult
from arquisys_ai.generators.plantuml.common import make_unique_id, quote_label
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


def generate_class_plantuml(analysis: AnalystResult) -> str:
    class_entries = analysis.classes or ["Sistema"]
    parsed = [_parse_class_entry(entry) for entry in class_entries]

    lines: list[str] = ["@startuml"]
    class_ids: list[str] = []
    used_ids: set[str] = set()

    for idx, (class_name, attrs) in enumerate(parsed, start=1):
        class_id = make_unique_id(class_name, f"Class{idx}", used_ids)
        class_ids.append(class_id)

        lines.append(f'class "{quote_label(class_name)}" as {class_id} {{')
        if attrs:
            for attr in attrs:
                attr_name = to_identifier(attr, fallback_prefix="field")
                field_name = attr_name[:1].lower() + attr_name[1:]
                lines.append(f"  +{field_name}: string")
        else:
            lines.append("  +id: string")
        lines.append("}")

    if len(class_ids) >= 2:
        lines.append(f"{class_ids[0]} --> {class_ids[1]} : relacion")

    lines.append("@enduml")
    return "\n".join(lines)
