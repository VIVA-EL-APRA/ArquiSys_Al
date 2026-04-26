from __future__ import annotations

import re

from arquisys_ai.core.models import AnalystResult
from arquisys_ai.generators.plantuml.common import dedupe, make_unique_id, quote_label
from arquisys_ai.utils.text import normalize_text


_INTERACTION_PATTERN = re.compile(r"^\s*(.+?)\s*(->>|-->>|->|-->)\s*(.+?)\s*:\s*(.+)\s*$")


def _parse_interaction(step: str) -> tuple[str, str, str, str] | None:
    match = _INTERACTION_PATTERN.match(step)
    if not match:
        return None

    sender = match.group(1).strip()
    arrow = match.group(2).strip()
    receiver = match.group(3).strip()
    message = quote_label(match.group(4).strip())
    if not sender or not receiver or not message:
        return None

    return sender, arrow, receiver, message


def _plantuml_arrow(mermaid_arrow: str) -> str:
    if mermaid_arrow == "-->>":
        return "-->"
    if mermaid_arrow == "->>":
        return "->"
    return mermaid_arrow


def _is_user_participant(name: str) -> bool:
    normalized = normalize_text(name)
    return any(token in normalized for token in ["usuario", "cliente", "user", "actor", "comprador"])


def generate_sequence_plantuml(analysis: AnalystResult) -> str:
    steps = analysis.sequence_steps or analysis.flow_steps or analysis.use_cases
    parsed_interactions = [_parse_interaction(step) for step in steps]

    participants = dedupe(analysis.participants or analysis.actors)
    for parsed in parsed_interactions:
        if parsed is None:
            continue
        participants.extend([parsed[0], parsed[2]])
    participants = dedupe(participants)

    if len(participants) < 2:
        participants = dedupe(participants + ["Usuario", "Sistema"])

    lines: list[str] = ["@startuml"]
    used_ids: set[str] = set()
    id_by_name: dict[str, str] = {}

    for idx, participant in enumerate(participants, start=1):
        participant_id = make_unique_id(participant, f"P{idx}", used_ids)
        id_by_name[participant] = participant_id

        kind = "actor" if _is_user_participant(participant) and idx == 1 else "participant"
        lines.append(f'{kind} "{quote_label(participant)}" as {participant_id}')

    if not steps:
        source = id_by_name[participants[0]]
        target = id_by_name[participants[1]]
        lines.append(f"{source} -> {target} : Solicitud principal")
        lines.append(f"{target} --> {source} : Respuesta")
        lines.append("@enduml")
        return "\n".join(lines)

    default_source = id_by_name[participants[0]]
    default_target = id_by_name[participants[1]]

    for index, raw_step in enumerate(steps):
        parsed = parsed_interactions[index]
        if parsed is None:
            lines.append(f"{default_source} -> {default_target} : {quote_label(raw_step)}")
            continue

        sender, arrow, receiver, message = parsed
        sender_id = id_by_name.get(sender, default_source)
        receiver_id = id_by_name.get(receiver, default_target)
        lines.append(f"{sender_id} {_plantuml_arrow(arrow)} {receiver_id} : {message}")

    lines.append("@enduml")
    return "\n".join(lines)
