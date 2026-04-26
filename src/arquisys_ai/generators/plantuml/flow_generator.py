from __future__ import annotations

from arquisys_ai.core.models import AnalystResult
from arquisys_ai.generators.plantuml.common import quote_label
from arquisys_ai.utils.text import normalize_text


def _pick_step(steps: list[str], tokens: list[str], default: str) -> str:
    for step in steps:
        normalized = normalize_text(step)
        if any(token in normalized for token in tokens):
            return quote_label(step)
    return default


def _looks_like_checkout_flow(steps: list[str]) -> bool:
    has_stock = any("stock" in normalize_text(step) or "inventario" in normalize_text(step) for step in steps)
    has_payment = any("pago" in normalize_text(step) or "tarjeta" in normalize_text(step) for step in steps)
    return has_stock and has_payment


def generate_flow_plantuml(analysis: AnalystResult) -> str:
    steps = analysis.flow_steps or ["Inicio", "Proceso", "Fin"]

    if _looks_like_checkout_flow(steps):
        start_label = _pick_step(steps, ["carrito", "inicio", "checkout"], "Iniciar checkout")
        stock_label = _pick_step(steps, ["stock", "inventario"], "Validar stock")
        payment_label = _pick_step(steps, ["pago", "autoriz", "tarjeta"], "Procesar pago")
        notify_label = _pick_step(steps, ["almacen", "notificar", "despacho"], "Notificar al almacen")
        stock_error_label = _pick_step(steps, ["falta de stock", "stock insuficiente"], "Manejar falta de stock")
        payment_error_label = _pick_step(steps, ["sin fondos", "rechaz", "fallo"], "Manejar pago rechazado")

        lines: list[str] = [
            "@startuml",
            "start",
            f":{start_label};",
            f":{stock_label};",
            "if (Stock disponible?) then (Si)",
            f"  :{payment_label};",
            "  if (Pago aprobado?) then (Si)",
            f"    :{notify_label};",
            "    stop",
            "  else (No)",
            f"    :{payment_error_label};",
            "    stop",
            "  endif",
            "else (No)",
            f"  :{stock_error_label};",
            "  stop",
            "endif",
            "@enduml",
        ]
        return "\n".join(lines)

    lines: list[str] = ["@startuml", "start"]
    for step in steps:
        lines.append(f":{quote_label(step)};")
    lines.append("stop")
    lines.append("@enduml")
    return "\n".join(lines)
