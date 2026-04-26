from __future__ import annotations

import re

from arquisys_ai.core.models import AnalystResult
from arquisys_ai.utils.text import mermaid_safe_label, normalize_text, to_identifier


def _dedupe(items: list[str]) -> list[str]:
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


def _make_unique_id(name: str, prefix: str, used: set[str]) -> str:
    base = to_identifier(name, fallback_prefix=prefix)
    base = (base[:1].lower() + base[1:]) if base else prefix
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _parse_container(entry: str) -> tuple[str, str]:
    match = re.match(r"\s*([^(]+?)\s*(?:\(([^)]*)\))?\s*$", entry)
    if not match:
        return entry.strip(), ""
    name = match.group(1).strip()
    tech = (match.group(2) or "").strip()
    return name, tech


def _split_relation(raw: str) -> tuple[str, str, str] | None:
    match = re.match(r"^\s*(.+?)\s*(?:->|-->)\s*(.+?)(?:\s*:\s*(.+))?\s*$", raw)
    if not match:
        return None
    source = match.group(1).strip()
    target = match.group(2).strip()
    label = mermaid_safe_label((match.group(3) or "Interacciona").strip())
    if not source or not target:
        return None
    return source, target, label


def _resolve(raw: str, ids_by_name: dict[str, str]) -> str | None:
    key = normalize_text(raw)
    for name, item_id in ids_by_name.items():
        if normalize_text(name) == key:
            return item_id
    return None


def generate_c4_container_mermaid(analysis: AnalystResult) -> str:
    systems = _dedupe(analysis.c4_systems or ["Sistema Principal"])
    people = _dedupe(analysis.c4_people or analysis.actors or ["Usuario"])
    container_entries = _dedupe(
        analysis.c4_containers or ["Web App(React)", "API(FastAPI)", "Base de Datos(PostgreSQL)"]
    )

    lines: list[str] = ["flowchart LR"]
    used_ids: set[str] = set()
    ids_by_name: dict[str, str] = {}

    for idx, person in enumerate(people, start=1):
        person_id = _make_unique_id(person, f"Person{idx}", used_ids)
        ids_by_name[person] = person_id
        lines.append(f'    {person_id}["Persona {mermaid_safe_label(person)}"]')

    primary_system = systems[0]
    lines.append(f'    subgraph SYSCONT["{mermaid_safe_label(primary_system)}"]')
    lines.append("        direction TB")

    container_ids: list[str] = []
    for idx, entry in enumerate(container_entries, start=1):
        name, tech = _parse_container(entry)
        container_id = _make_unique_id(name, f"Container{idx}", used_ids)
        ids_by_name[name] = container_id
        container_ids.append(container_id)

        tech_label = f" ({mermaid_safe_label(tech)})" if tech else ""
        lines.append(f'        {container_id}["{mermaid_safe_label(name)}{tech_label}"]')

    lines.append("    end")

    for external in systems[1:]:
        external_id = _make_unique_id(external, "ExternalSystem", used_ids)
        ids_by_name[external] = external_id
        lines.append(f'    {external_id}["Sistema externo {mermaid_safe_label(external)}"]')

    relation_lines: list[str] = []
    for relation in analysis.c4_relations:
        split = _split_relation(relation)
        if split is None:
            continue
        source, target, label = split
        source_id = _resolve(source, ids_by_name)
        target_id = _resolve(target, ids_by_name)
        if not source_id or not target_id:
            continue
        relation_lines.append(f"    {source_id} -->|{label}| {target_id}")

    if not relation_lines and container_ids:
        first_container = container_ids[0]
        for person in people:
            relation_lines.append(f"    {ids_by_name[person]} -->|Usa| {first_container}")

        for left, right in zip(container_ids, container_ids[1:]):
            relation_lines.append(f"    {left} -->|Intercambia datos| {right}")

    lines.extend(relation_lines)
    return "\n".join(lines)
