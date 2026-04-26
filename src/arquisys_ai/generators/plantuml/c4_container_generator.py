from __future__ import annotations

import re

from arquisys_ai.core.models import AnalystResult
from arquisys_ai.generators.plantuml.common import dedupe, make_unique_id, quote_label
from arquisys_ai.utils.text import normalize_text


def _parse_container(entry: str) -> tuple[str, str]:
    match = re.match(r"\s*([^(]+?)\s*(?:\(([^)]*)\))?\s*$", entry)
    if not match:
        return entry.strip(), ""
    return match.group(1).strip(), (match.group(2) or "").strip()


def _split_relation(raw: str) -> tuple[str, str, str] | None:
    match = re.match(r"^\s*(.+?)\s*(?:->|-->)\s*(.+?)(?:\s*:\s*(.+))?\s*$", raw)
    if not match:
        return None
    source = match.group(1).strip()
    target = match.group(2).strip()
    label = quote_label((match.group(3) or "Integra").strip())
    if not source or not target:
        return None
    return source, target, label


def _resolve(raw: str, ids_by_name: dict[str, str]) -> str | None:
    key = normalize_text(raw)
    for name, value in ids_by_name.items():
        if normalize_text(name) == key:
            return value
    return None


def generate_c4_container_plantuml(analysis: AnalystResult) -> str:
    systems = dedupe(analysis.c4_systems or ["Sistema Principal"])
    people = dedupe(analysis.c4_people or analysis.actors or ["Usuario"])
    container_entries = dedupe(
        analysis.c4_containers or ["Web App(React)", "API(FastAPI)", "Base de Datos(PostgreSQL)"]
    )

    lines: list[str] = ["@startuml", "left to right direction"]
    used_ids: set[str] = set()
    ids_by_name: dict[str, str] = {}

    for idx, person in enumerate(people, start=1):
        person_id = make_unique_id(person, f"P{idx}", used_ids)
        ids_by_name[person] = person_id
        lines.append(f'actor "{quote_label(person)}" as {person_id}')

    system_id = make_unique_id(systems[0], "SYS", used_ids)
    lines.append(f'package "{quote_label(systems[0])}" {{')

    container_ids: list[str] = []
    for idx, entry in enumerate(container_entries, start=1):
        name, tech = _parse_container(entry)
        container_id = make_unique_id(name, f"C{idx}", used_ids)
        ids_by_name[name] = container_id
        container_ids.append(container_id)
        tech_suffix = f"\\n[{quote_label(tech)}]" if tech else ""
        lines.append(f'  rectangle "{quote_label(name)}{tech_suffix}" as {container_id}')

    lines.append("}")
    ids_by_name[systems[0]] = system_id

    for external in systems[1:]:
        external_id = make_unique_id(external, "EXT", used_ids)
        ids_by_name[external] = external_id
        lines.append(f'rectangle "{quote_label(external)}" as {external_id}')

    relation_count = 0
    for relation in analysis.c4_relations:
        split = _split_relation(relation)
        if split is None:
            continue
        source, target, label = split
        source_id = _resolve(source, ids_by_name)
        target_id = _resolve(target, ids_by_name)
        if not source_id or not target_id:
            continue
        lines.append(f"{source_id} --> {target_id} : {label}")
        relation_count += 1

    if relation_count == 0:
        if container_ids:
            first_container = container_ids[0]
            for person in people:
                lines.append(f"{ids_by_name[person]} --> {first_container} : Usa")
            for left, right in zip(container_ids, container_ids[1:]):
                lines.append(f"{left} --> {right} : Integra")

    lines.append("@enduml")
    return "\n".join(lines)
