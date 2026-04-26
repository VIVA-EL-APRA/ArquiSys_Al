from __future__ import annotations

import re

from arquisys_ai.core.models import AnalystResult
from arquisys_ai.utils.text import mermaid_safe_label


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "accion"


def _pick_scope(analysis: AnalystResult) -> list[str]:
    if analysis.use_cases:
        return analysis.use_cases
    if analysis.flow_steps:
        return analysis.flow_steps
    if analysis.sequence_steps:
        return analysis.sequence_steps
    if analysis.classes:
        return analysis.classes
    if analysis.entities:
        return analysis.entities
    return ["operacion-principal"]


def _pick_stack(analysis: AnalystResult) -> list[str]:
    return analysis.stack or ["FastAPI", "PostgreSQL", "React"]


def generate_scaffolding_plan(analysis: AnalystResult) -> str:
    scope = _pick_scope(analysis)
    stack = _pick_stack(analysis)

    lines: list[str] = [
        "# Scaffolding Base del Sistema",
        "",
        "## Stack detectado",
        f"- {', '.join(stack)}",
        "",
        "## Estructura sugerida",
        "```text",
        "project/",
        "  backend/",
        "    app/",
        "      main.py",
        "      routes/",
        "      services/",
        "      models/",
        "  frontend/",
        "    src/",
        "      pages/",
        "      components/",
        "  tests/",
        "    api/",
        "    e2e/",
        "```",
        "",
        "## Endpoints iniciales",
    ]

    for item in scope:
        clean = mermaid_safe_label(item)
        lines.append(f"- POST /api/{_slugify(clean)}")

    lines.extend(
        [
            "",
            "## Stub backend (ejemplo FastAPI)",
            "```python",
            "from fastapi import APIRouter",
            "",
            "router = APIRouter(prefix='/api', tags=['generated'])",
            "",
        ]
    )

    for item in scope[:4]:
        slug = _slugify(item)
        func_name = slug.replace("-", "_")
        lines.extend(
            [
                f"@router.post('/{slug}')",
                f"def {func_name}():",
                f"    return {{'status': 'ok', 'action': '{slug}'}}",
                "",
            ]
        )

    lines.append("```")
    lines.append("")
    lines.append("## Proximo paso")
    lines.append("- Conectar estos stubs con reglas de dominio y pruebas de QA.")

    return "\n".join(lines)
