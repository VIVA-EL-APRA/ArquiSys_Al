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


def extract_narrative_steps(text: str) -> list[str]:
    steps: list[str] = []
    
    paso_pattern = re.findall(
        r"(?:^|\n)\s*(?:paso\s*)?(\d+)[\:\.]\s*([^\n]+)",
        text,
        flags=re.IGNORECASE
    )
    if paso_pattern:
        steps.extend([f"{num}. {step.strip()}" for num, step in paso_pattern if step.strip()])
    
    if steps:
        return steps
    
    action_patterns = [
        r"(?:^|\n)\s*las\s+acciones\s+(?:principales\s+)?son[\:\-]?\s*([^\n]+)",
        r"(?:^|\n)\s*los\s+pasos\s+(?:principales\s+)?son[\:\-]?\s*([^\n]+)",
        r"(?:^|\n)\s*el\s+flujo\s+es[\:\-]?\s*([^\n]+)",
        r"(?:^|\n)\s*flujo\s+principal[\:\-]?\s*([^\n]+)",
        r"(?:^|\n)\s*el\s+proceso\s+es[\:\-]?\s*([^\n]+)",
    ]
    
    for pattern in action_patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        for match in matches:
            items = split_csv_items(match)
            steps.extend(items)
    
    if steps:
        return _dedupe_list(steps)
    
    inline_steps = re.findall(
        r"(?:^|\n)\s*(?:el\s+)?(?:cliente|usuario|cliente|comercio|sistema)\s+(?:hace|realiza|envía|recibe|invoca|llama)\s+([^\n]+)",
        text,
        flags=re.IGNORECASE
    )
    if inline_steps:
        return _dedupe_list([s.strip() for s in inline_steps if s.strip()])
    
    return []


def _dedupe_list(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = normalize_text(item)
        if key and key not in seen:
            seen.add(key)
            result.append(item.strip())
    return result


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
