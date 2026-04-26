from __future__ import annotations

import re

from arquisys_ai.core.models import AnalystResult
from arquisys_ai.utils.text import mermaid_safe_label, normalize_text, to_identifier


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for item in items:
        clean = item.strip()
        if not clean:
            continue
        key = normalize_text(clean)
        if key in seen:
            continue
        seen.add(key)
        output.append(clean)
    return output


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


def generate_c4_context_mermaid(analysis: AnalystResult) -> str:
    people = _dedupe(analysis.c4_people or analysis.actors or ["Usuario"])
    systems = _dedupe(analysis.c4_systems or ["Sistema Principal"])

    lines: list[str] = ["flowchart LR"]
    used_ids: set[str] = set()
    ids_by_name: dict[str, str] = {}

    for idx, person in enumerate(people, start=1):
        person_id = _make_unique_id(person, f"Person{idx}", used_ids)
        ids_by_name[person] = person_id
        lines.append(f'    {person_id}["Persona {mermaid_safe_label(person)}"]')

    lines.append('    subgraph SYSCTX["Contexto del sistema"]')
    lines.append("        direction TB")
    for idx, system in enumerate(systems, start=1):
        system_id = _make_unique_id(system, f"System{idx}", used_ids)
        ids_by_name[system] = system_id
        lines.append(f'        {system_id}["Sistema {mermaid_safe_label(system)}"]')
    lines.append("    end")

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

    if not relation_lines:
        primary_system = ids_by_name[systems[0]]
        for person in people:
            person_id = ids_by_name[person]
            relation_lines.append(f"    {person_id} -->|Usa| {primary_system}")

    lines.extend(relation_lines)
    return "\n".join(lines)
