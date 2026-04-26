from __future__ import annotations

import re

from arquisys_ai.core.models import AnalystResult
from arquisys_ai.utils.text import mermaid_safe_label, to_identifier


_INTERACTION_PATTERN = re.compile(r"^\s*(.+?)\s*(->>|-->>|->|-->)\s*(.+?)\s*:\s*(.+)\s*$")
_RESERVED_IDS = {
    "end",
    "participant",
    "actor",
    "loop",
    "alt",
    "opt",
    "par",
    "and",
    "note",
    "rect",
    "sequencediagram",
    "title",
}


def _dedupe(items: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for item in items:
        token = item.strip()
        if not token:
            continue
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(token)
    return unique


def _unique_identifier(name: str, fallback: str, used_ids: set[str]) -> str:
    base = to_identifier(name, fallback_prefix=fallback)
    if base.lower() in _RESERVED_IDS:
        base = f"{fallback}{base}"
    candidate = base
    suffix = 2
    while candidate in used_ids:
        candidate = f"{base}{suffix}"
        suffix += 1
    used_ids.add(candidate)
    return candidate


def _parse_interaction(step: str) -> tuple[str, str, str, str] | None:
    match = _INTERACTION_PATTERN.match(step)
    if not match:
        return None

    sender = match.group(1).strip()
    arrow = match.group(2).strip()
    receiver = match.group(3).strip()
    message = mermaid_safe_label(match.group(4).strip())
    if not sender or not receiver or not message:
        return None

    return sender, arrow, receiver, message


def generate_sequence_mermaid(analysis: AnalystResult) -> str:
    steps = analysis.sequence_steps or analysis.flow_steps or analysis.use_cases
    parsed_interactions = [_parse_interaction(step) for step in steps]

    participants = _dedupe(analysis.participants or analysis.actors)
    for parsed in parsed_interactions:
        if parsed is None:
            continue
        participants.extend([parsed[0], parsed[2]])

    participants = _dedupe(participants)
    if len(participants) < 2:
        participants = _dedupe(participants + ["Usuario", "Sistema"])

    used_ids: set[str] = set()
    id_by_name: dict[str, str] = {}
    lines: list[str] = ["sequenceDiagram"]

    for idx, participant in enumerate(participants, start=1):
        participant_id = _unique_identifier(participant, f"P{idx}", used_ids)
        id_by_name[participant] = participant_id
        label = mermaid_safe_label(participant)
        lines.append(f'    participant {participant_id} as "{label}"')

    if not steps:
        source = id_by_name[participants[0]]
        target = id_by_name[participants[1]]
        lines.append(f"    {source}->>{target}: Solicitud principal")
        lines.append(f"    {target}-->>{source}: Respuesta")
        return "\n".join(lines)

    default_source = id_by_name[participants[0]]
    default_target = id_by_name[participants[1]]

    for index, raw_step in enumerate(steps):
        parsed = parsed_interactions[index]
        if parsed is None:
            message = mermaid_safe_label(raw_step)
            lines.append(f"    {default_source}->>{default_target}: {message}")
            continue

        sender, arrow, receiver, message = parsed
        sender_id = id_by_name.get(sender, default_source)
        receiver_id = id_by_name.get(receiver, default_target)
        lines.append(f"    {sender_id}{arrow}{receiver_id}: {message}")

    return "\n".join(lines)
