from __future__ import annotations

from arquisys_ai.core.models import AnalystResult
from arquisys_ai.utils.text import mermaid_safe_label


def _collect_scenarios(analysis: AnalystResult) -> list[str]:
    if analysis.use_cases:
        return analysis.use_cases
    if analysis.sequence_steps:
        return analysis.sequence_steps
    if analysis.flow_steps:
        return analysis.flow_steps
    return ["Flujo principal del sistema"]


def generate_qa_test_cases(analysis: AnalystResult) -> str:
    scenarios = _collect_scenarios(analysis)
    lines: list[str] = [
        "# QA Automatico - Escenarios Base",
        "",
        "## Formato Gherkin sugerido",
        "",
    ]

    for idx, scenario in enumerate(scenarios, start=1):
        label = mermaid_safe_label(scenario)
        lines.extend(
            [
                f"### Escenario {idx}: {label}",
                "```gherkin",
                f"Scenario: {label}",
                "  Given el usuario tiene contexto valido",
                f"  When ejecuta la accion '{label}'",
                "  Then el sistema responde con resultado esperado",
                "```",
                "",
            ]
        )

    lines.extend(
        [
            "## Checklist de verificacion",
            "- Validar respuesta exitosa.",
            "- Validar errores de entrada y mensajes de negocio.",
            "- Validar persistencia o efectos secundarios.",
            "- Validar autorizacion y permisos cuando aplique.",
        ]
    )
    return "\n".join(lines)
