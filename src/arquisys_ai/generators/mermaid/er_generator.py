from __future__ import annotations

import re

from arquisys_ai.core.models import AnalystResult
from arquisys_ai.utils.text import mermaid_safe_label, normalize_text, to_identifier


_RELATION_TOKENS = [
    "||--o{",
    "||--|{",
    "||--||",
    "|{--||",
    "}o--||",
    "}o--|{",
    "}o--o{",
    "|o--||",
    "|o--o{",
]


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


def _unique_entity_id(name: str, idx: int, used_ids: set[str]) -> str:
    base = to_identifier(name, fallback_prefix=f"Entity{idx}").upper()
    candidate = base
    suffix = 2
    while candidate in used_ids:
        candidate = f"{base}{suffix}"
        suffix += 1
    used_ids.add(candidate)
    return candidate


def _resolve_entity_id(raw: str, by_name: dict[str, str]) -> str | None:
    normalized = normalize_text(raw)
    for name, entity_id in by_name.items():
        if normalize_text(name) == normalized:
            return entity_id
    return None


def _parse_relationship(rel: str, by_name: dict[str, str]) -> str | None:
    clean = rel.strip()
    if not clean:
        return None

    for token in _RELATION_TOKENS:
        if token in clean:
            left, right_part = clean.split(token, maxsplit=1)
            right, _, label = right_part.partition(":")
            left_id = _resolve_entity_id(left.strip(), by_name)
            right_id = _resolve_entity_id(right.strip(), by_name)
            if not left_id or not right_id:
                return None
            relation_label = mermaid_safe_label(label.strip()) if label.strip() else "relacion"
            return f"    {left_id} {token} {right_id} : {relation_label}"

    arrow_match = re.match(r"^\s*(.+?)\s*(?:->|-->)\s*(.+?)(?:\s*:\s*(.+))?\s*$", clean)
    if arrow_match:
        left_id = _resolve_entity_id(arrow_match.group(1).strip(), by_name)
        right_id = _resolve_entity_id(arrow_match.group(2).strip(), by_name)
        if not left_id or not right_id:
            return None
        label = mermaid_safe_label((arrow_match.group(3) or "relacion").strip())
        return f"    {left_id} ||--o{{ {right_id} : {label}"

    return None


def generate_er_mermaid(analysis: AnalystResult) -> str:
    entity_entries = analysis.entities or analysis.classes or ["Entidad(id)"]
    parsed_entities = [_parse_entity_entry(entry) for entry in entity_entries]

    lines: list[str] = ["erDiagram"]
    used_ids: set[str] = set()
    entity_ids: list[str] = []
    ids_by_raw_name: dict[str, str] = {}

    for idx, (entity_name, attrs) in enumerate(parsed_entities, start=1):
        entity_id = _unique_entity_id(entity_name, idx, used_ids)
        entity_ids.append(entity_id)
        ids_by_raw_name[entity_name] = entity_id

        lines.append(f"    {entity_id} {{")
        if attrs:
            for attr in attrs:
                attr_id = to_identifier(attr, fallback_prefix="field")
                attr_name = attr_id[:1].lower() + attr_id[1:]
                lines.append(f"        string {attr_name}")
        else:
            lines.append("        string id")
        lines.append("    }")

    relation_lines = [
        parsed
        for parsed in (_parse_relationship(relation, ids_by_raw_name) for relation in analysis.relationships)
        if parsed is not None
    ]

    if not relation_lines and len(entity_ids) >= 2:
        relation_lines.append(f"    {entity_ids[0]} ||--o{{ {entity_ids[1]} : relacion")

    lines.extend(relation_lines)
    return "\n".join(lines)
