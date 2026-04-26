from __future__ import annotations

import re

from arquisys_ai.core.models import AnalystResult
from arquisys_ai.generators.plantuml.common import make_unique_id, quote_label
from arquisys_ai.utils.text import to_identifier


def _parse_entity_entry(entry: str) -> tuple[str, list[str]]:
    match = re.match(r"\s*([^(]+?)\s*(?:\(([^)]*)\))?\s*$", entry)
    if not match:
        return entry.strip(), []

    entity_name = match.group(1).strip()
    attrs_raw = match.group(2)
    if not attrs_raw:
        return entity_name, []

    attrs = [item.strip() for item in attrs_raw.split(",") if item.strip()]
    return entity_name, attrs


def _parse_relationship(rel: str) -> tuple[str, str, str] | None:
    match = re.match(r"^\s*(.+?)\s*(?:->|-->)\s*(.+?)(?:\s*:\s*(.+))?\s*$", rel)
    if not match:
        return None

    left = match.group(1).strip()
    right = match.group(2).strip()
    label = quote_label((match.group(3) or "relacion").strip())
    if not left or not right:
        return None
    return left, right, label


def generate_er_plantuml(analysis: AnalystResult) -> str:
    entity_entries = analysis.entities or analysis.classes or ["Entidad(id)"]
    parsed_entities = [_parse_entity_entry(entry) for entry in entity_entries]

    lines: list[str] = ["@startuml", "hide circle"]
    used_ids: set[str] = set()
    ids_by_name: dict[str, str] = {}
    entity_ids: list[str] = []

    for idx, (entity_name, attrs) in enumerate(parsed_entities, start=1):
        entity_id = make_unique_id(entity_name, f"E{idx}", used_ids)
        ids_by_name[entity_name] = entity_id
        entity_ids.append(entity_id)

        lines.append(f'entity "{quote_label(entity_name)}" as {entity_id} {{')
        if attrs:
            first = attrs[0]
            first_name = to_identifier(first, fallback_prefix="id")
            lines.append(f"  * {first_name[:1].lower() + first_name[1:]} : string")
            for attr in attrs[1:]:
                attr_name = to_identifier(attr, fallback_prefix="field")
                lines.append(f"  {attr_name[:1].lower() + attr_name[1:]} : string")
        else:
            lines.append("  * id : string")
        lines.append("}")

    relation_count = 0
    for relation in analysis.relationships:
        parsed = _parse_relationship(relation)
        if parsed is None:
            continue
        left, right, label = parsed
        left_id = ids_by_name.get(left)
        right_id = ids_by_name.get(right)
        if not left_id or not right_id:
            continue
        lines.append(f"{left_id} ||--o{{ {right_id} : {label}")
        relation_count += 1

    if relation_count == 0 and len(entity_ids) >= 2:
        lines.append(f"{entity_ids[0]} ||--o{{ {entity_ids[1]} : relacion")

    lines.append("@enduml")
    return "\n".join(lines)
