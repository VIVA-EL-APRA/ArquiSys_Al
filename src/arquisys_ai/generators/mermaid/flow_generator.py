from __future__ import annotations

from arquisys_ai.core.models import AnalystResult
from arquisys_ai.utils.text import mermaid_safe_label, normalize_text


def _pick_step(steps: list[str], tokens: list[str], default: str) -> str:
    for step in steps:
        normalized = normalize_text(step)
        if any(token in normalized for token in tokens):
            return mermaid_safe_label(step)
    return default


def _looks_like_checkout_flow(steps: list[str]) -> bool:
    has_stock = any("stock" in normalize_text(step) or "inventario" in normalize_text(step) for step in steps)
    has_payment = any("pago" in normalize_text(step) or "tarjeta" in normalize_text(step) for step in steps)
    return has_stock and has_payment


def generate_flow_mermaid(analysis: AnalystResult) -> str:
    steps = analysis.flow_steps or ["Inicio", "Proceso", "Fin"]

    if _looks_like_checkout_flow(steps):
        start_label = _pick_step(steps, ["carrito", "inicio", "checkout"], "Iniciar checkout")
        stock_label = _pick_step(steps, ["stock", "inventario"], "Validar stock")
        payment_label = _pick_step(steps, ["pago", "autoriz", "tarjeta"], "Procesar pago")
        notify_label = _pick_step(steps, ["almacen", "notificar", "despacho"], "Notificar al almacen")
        stock_error_label = _pick_step(steps, ["falta de stock", "stock insuficiente"], "Manejar falta de stock")
        payment_error_label = _pick_step(steps, ["sin fondos", "rechaz", "fallo"], "Manejar pago rechazado")

        lines: list[str] = [
            "flowchart TD",
            '    S(["Inicio"])',
            f'    C["{start_label}"]',
            f'    V["{stock_label}"]',
            '    D1{"Stock disponible?"}',
            f'    P["{payment_label}"]',
            '    D2{"Pago aprobado?"}',
            f'    N["{notify_label}"]',
            '    OK(["Fin exitoso"])',
            f'    E1["{stock_error_label}"]',
            f'    E2["{payment_error_label}"]',
            '    FAIL(["Fin con incidencia"])',
            "    S --> C --> V --> D1",
            "    D1 -- Si --> P",
            "    D1 -- No --> E1 --> FAIL",
            "    P --> D2",
            "    D2 -- Si --> N --> OK",
            "    D2 -- No --> E2 --> FAIL",
        ]
        return "\n".join(lines)

    lines: list[str] = ["flowchart TD"]
    step_ids: list[str] = []

    for idx, step in enumerate(steps, start=1):
        step_id = f"N{idx}"
        step_ids.append(step_id)
        lines.append(f'    {step_id}["{mermaid_safe_label(step)}"]')

    for prev, nxt in zip(step_ids, step_ids[1:]):
        lines.append(f"    {prev} --> {nxt}")

    return "\n".join(lines)
