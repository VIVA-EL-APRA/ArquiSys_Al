from __future__ import annotations

import re
import unicodedata


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()


def split_csv_items(raw: str) -> list[str]:
    cleaned = raw
    separators = {",", ";", "|", "/"}

    items: list[str] = []
    current: list[str] = []
    depth_parentheses = 0
    depth_brackets = 0
    depth_braces = 0

    for char in cleaned:
        if char == "(":
            depth_parentheses += 1
        elif char == ")":
            depth_parentheses = max(0, depth_parentheses - 1)
        elif char == "[":
            depth_brackets += 1
        elif char == "]":
            depth_brackets = max(0, depth_brackets - 1)
        elif char == "{":
            depth_braces += 1
        elif char == "}":
            depth_braces = max(0, depth_braces - 1)

        should_split = (
            char in separators
            and depth_parentheses == 0
            and depth_brackets == 0
            and depth_braces == 0
        )

        if should_split:
            token = "".join(current).strip(" .:-")
            if token:
                items.append(token)
            current = []
            continue

        current.append(char)

    final_token = "".join(current).strip(" .:-")
    if final_token:
        items.append(final_token)

    return items


def extract_list_after_labels(text: str, labels: list[str]) -> list[str]:
    for label in labels:
        pattern = rf"(?<!\w){re.escape(label)}(?!\w)\s*:\s*([^\n\r\.]+)"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return split_csv_items(match.group(1))
    return []


def extract_numbered_steps(text: str) -> list[str]:
    numbered = re.findall(r"(?:^|\n)\s*\d+[\)\.\-]\s*([^\n]+)", text)
    if numbered:
        return [step.strip() for step in numbered if step.strip()]

    bulleted = re.findall(r"(?:^|\n)\s*[-*]\s*([^\n]+)", text)
    if bulleted:
        return [step.strip() for step in bulleted if step.strip()]

    return []


def mermaid_safe_label(text: str) -> str:
    safe = text.replace('"', "'").strip()
    safe = re.sub(r"\s+", " ", safe)
    safe = (
        safe.replace("[", "(")
        .replace("]", ")")
        .replace("{", "(")
        .replace("}", ")")
        .replace("<", "(")
        .replace(">", ")")
    )
    return safe if safe else "Item"


def to_identifier(text: str, fallback_prefix: str = "Node") -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", ascii_text) if part]

    if not parts:
        return fallback_prefix

    identifier = "".join(part[:1].upper() + part[1:] for part in parts)
    if identifier[0].isdigit():
        return f"{fallback_prefix}{identifier}"
    return identifier
